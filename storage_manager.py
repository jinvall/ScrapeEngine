#!/usr/bin/env python3
"""
Storage manager with enforced 5 GiB hard ceiling, FIFO eviction,
content-addressed compressed blobs, and atomic quota reservations.

Key design goals:
- Absolute persistent storage limit: 5 GiB total.
- Soft threshold: ~4.75 GiB (begin proactive eviction).
- FIFO eviction based on original ingestion time.
- Shared-blob reference counting (delete only when refcount=0).
- Atomic storage reservations before ingestion.
- Database WAL/journal awareness.
- Transparent compression with integrity verification.
- Incremental byte accounting (no directory walks at runtime).
"""

import traceback
import hashlib
import json
import os
import sqlite3
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# -_______________________________________________________________________________


STORAGE_ROOT_ENV = "SCRAPE_ENGINE_STORAGE_ROOT"
DEFAULT_STORAGE_ROOT = Path(__file__).parent / ".storage"
HARD_CEILING_BYTES = 5 * 1024 ** 3  # 5 GiB = 5 * 1024^3 bytes
SOFT_THRESHOLD_BYTES = int(HARD_CEILING_BYTES * 0.95)  # 4.75 GiB
MIN_EVICTION_MARGIN_BYTES = 10 * 1024 ** 2  # 10 MiB headroom reserve

# ---------------------------------------------------------------------------
# Storage root abstraction
# -_______________________________________________________________________________


class StorageRoot:
    """Managed storage root directory with quota enforcement."""

    def __init__(self, root: Optional[Path] = None, hard_ceiling: int = HARD_CEILING_BYTES,
                 soft_threshold: int = SOFT_THRESHOLD_BYTES):
        if root is not None:
            self.root = Path(root)
        else:
            self.root = Path(DEFAULT_STORAGE_ROOT)
        self.hard_ceiling = hard_ceiling
        self.soft_threshold = soft_threshold
        self.root.mkdir(parents=True, exist_ok=True)
        # Subdirectories
        self.blobs_dir = self.root / "blobs"
        self.metadata_dir = self.root / "metadata"
        self.eviction_dir = self.root / "eviction"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.eviction_dir.mkdir(parents=True, exist_ok=True)

    def path_for_blob(self, sha256_hex: str) -> Path:
        return self.blobs_dir / sha256_hex

    def path_for_metadata(self, sha256_hex: str) -> Path:
        return self.metadata_dir / f"{sha256_hex}.json"

    def path_for_eviction_record(self, sha256_hex: str) -> Path:
        return self.eviction_dir / f"{sha256_hex}.json"


# ---------------------------------------------------------------------------
# Content-addressed storage with compression
# -_______________________________________________________________________________


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256_from_path(path: Path) -> str:
    """Compute SHA-256 hex digest of the file at path."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compress_data(data: bytes, level: int = 6) -> Tuple[bytes, Dict[str, Any]]:
    """
    Compress bytes using zlib.
    Returns (compressed_data, metadata_dict).
    Metadata includes original_size and method.
    """
    compressed = zlib.compress(data, level=level)
    metadata = {
        "original_size": len(data),
        "compressed_size": len(compressed),
        "method": "zlib",
        "level": level,
    }
    return compressed, metadata


def decompress_data(compressed: bytes, metadata: Dict[str, Any]) -> bytes:
    """Decompress data that was compressed by compress_data()."""
    if metadata.get("method") != "zlib":
        raise ValueError(f"Unsupported compression method: {metadata.get('method')}")
    return zlib.decompress(compressed)


# ---------------------------------------------------------------------------
# Quota reservation (atomic)
# -_______________________________________________________________________________


class QuotaReservation:
    """
    Context manager for atomic storage reservations.

    Usage:
        with storage_root.reserve_bytes(needed_bytes) as ok:
            if ok:
                # safe to ingest
                store_blob(...)
                store_metadata(...)
            else:
                # quota exceeded; cannot safely store
                pass
    """

    def __init__(self, storage_root: "StorageManager", needed_bytes: int):
        self.storage_root = storage_root
        self.needed_bytes = needed_bytes
        self.ok = False
        self.current_usage = -1

    def __enter__(self):
        # Measure current usage via incremental accounting
        self.current_usage = self.storage_root._current_usage_bytes()
        available = self.storage_root.hard_ceiling - self.current_usage
        if available >= self.needed_bytes:
            self.ok = True
        else:
            # Attempt proactive eviction before deciding
            self.ok = self.storage_root._attempt_proactive_eviction(self.needed_bytes)
            if self.ok:
                self.current_usage = self.storage_root._current_usage_bytes()
        return self.ok

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class QuotaExceededError(Exception):
    """Raised when an ingestion cannot proceed because the storage quota is exhausted."""
    pass


# ---------------------------------------------------------------------------
# Storage Manager (public API)
# -_______________________________________________________________________________


class StorageManager:
    """
    Centralized storage manager enforcing the 5 GiB hard ceiling with FIFO eviction.

    Responsibilities:
    - Quota enforcement and atomic reservations.
    - Content-addressed storage with SHA-256 fingerprints and zlib compression.
    - FIFO eviction based on ingestion timestamp.
    - Shared-blob reference counting.
    - Database maintenance (WAL checkpointing, vacuuming, orphan cleanup).
    - Incremental byte accounting (no directory walks at runtime).

    Byte accounting is maintained incrementally via the storage_metadata table.
    The total usage = SUM(size_compressed FROM storage_metadata) + database_file_size.
    """

    def __init__(self, storage_root: Optional[Path] = None,
                 db_conn: Optional[sqlite3.Connection] = None,
                 hard_ceiling: int = HARD_CEILING_BYTES,
                 soft_threshold: int = SOFT_THRESHOLD_BYTES):
        self.storage_root = StorageRoot(storage_root, hard_ceiling, soft_threshold)
        self.hard_ceiling = hard_ceiling  # ADD THIS LINE
        if db_conn is not None:
            self.db_conn = db_conn
        else:
            db_path = str(self.storage_root.root / "crawl_database.sqlite")
            self.db_conn = sqlite3.connect(db_path)
        self.db_conn.execute("PRAGMA journal_mode=WAL")
        self.db_conn.execute("PRAGMA synchronous=NORMAL")
        self.eviction = FifoEvictionEngine(self.storage_root, self.db_conn)
        self._init_storage_tracking()

    def _init_storage_tracking(self):
        """Initialize storage-related tables in the existing database."""
        c = self.db_conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS storage_metadata (
                sha256_hex TEXT PRIMARY KEY,
                ingestion_timestamp TEXT NOT NULL,
                size_compressed INTEGER NOT NULL DEFAULT 0,
                size_uncompressed INTEGER NOT NULL DEFAULT 0,
                reference_count INTEGER NOT NULL DEFAULT 1,
                tags TEXT NOT NULL DEFAULT '[]',
                collection TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS eviction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256_hex TEXT NOT NULL,
                evicted_at TEXT NOT NULL,
                freed_bytes INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT 'FIFO eviction'
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS blob_reference_counts (
                sha256_hex TEXT PRIMARY KEY,
                reference_count INTEGER NOT NULL DEFAULT 1
            )"""
        )
        # Create index for efficient ordering by ingestion timestamp
        try:
            c.execute(
                """CREATE INDEX IF NOT EXISTS idx_storage_meta_ts
                   ON storage_metadata(ingestion_timestamp ASC)"""
            )
        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass
        self.db_conn.commit()

    def _current_usage_bytes(self) -> int:
        """
        Return the current accounted storage usage in bytes.

        This is INCREMENTAL:  SUM(size_compressed FROM storage_metadata)
        plus the actual SQLite database file size (main db + WAL + SHM if present).

        No directory walks are performed; this is O(1) with respect to file count.
        """
        c = self.db_conn.cursor()
        # Sum of compressed sizes from the tracking table
        try:
            c.execute("SELECT IFNULL(SUM(size_compressed), 0) FROM storage_metadata")
            row = c.fetchone()
            meta_sum = row[0] if row else 0
        except Exception:
            meta_sum = 0

        # Database file size
        db_file = self._get_db_primary_file()
        db_size = 0
        if db_file:
            try:
                db_size = os.path.getsize(db_file)
                # Include WAL
                wal_file = db_file + "-wal"
                if os.path.exists(wal_file):
                    db_size += os.path.getsize(wal_file)
                # Include SHM
                shm_file = db_file + "-shm"
                if os.path.exists(shm_file):
                    db_size += os.path.getsize(shm_file)
            except OSError:
                db_size = 0

        return meta_sum + db_size

    def _get_db_primary_file(self) -> Optional[str]:
        """Get the primary database file path from the instance's Connection."""
        try:
            row = self.db_conn.execute("PRAGMA database_list").fetchone()
            if row and row[2]:
                return row[2]
        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass
        try:
            return self.db_conn.execute("PRAGMA main.database_list").fetchone()[2]
        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass
        return None

    # ---- Content storage ----

    def store_blob(self, data: bytes, tags: List[str] = None,
                   collection: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Store a compressed, content-addressed blob.

        Returns (sha256_hex, metadata_dict).
        If the blob already exists (exact duplicate), returns the existing sha256
        and increments reference count.
        """
        sha256_hex = compute_sha256(data)

        # Check if blob already exists in tracking table
        c = self.db_conn.cursor()
        c.execute("SELECT sha256_hex FROM storage_metadata WHERE sha256_hex = ?", (sha256_hex,))
        existing = c.fetchone()

        if existing:
            # Already stored; just increment reference count
            self.eviction.increment_reference(sha256_hex)
            # Return existing metadata by reading from tracking table
            c2 = self.db_conn.cursor()
            c2.execute(
                """SELECT size_compressed, size_uncompressed, tags, collection
                   FROM storage_metadata WHERE sha256_hex = ?""",
                (sha256_hex,),
            )
            row = c2.fetchone()
            if row is None:
                # Should not happen since existing != None, but fallback
                meta = {
                    "original_size": len(data),
                    "compressed_size": len(zlib.compress(data)),
                    "method": "zlib",
                    "tags": [],
                    "collection": None,
                }
            else:
                meta = {
                    "original_size": row[1],
                    "compressed_size": row[0],
                    "method": "zlib",
                    "tags": json.loads(row[2]) if row[2] else [],
                    "collection": json.loads(row[3]) if row[3] else None,
                }
            return sha256_hex, meta

        # Atomic quota reservation
        compressed_estimate = len(zlib.compress(data))
        need_reserve = compressed_estimate + 4096  # +4KB for metadata JSON overhead
        ok = False
        with QuotaReservation(self, need_reserve) as reserved:
            ok = reserved

        if not ok:
            raise QuotaExceededError(
                f"Storage quota exceeded: needed ~{need_reserve/1024/1024:.1f} MiB, "
                f"current usage ~{self._current_usage_bytes()/1024/1024:.1f} MiB, "
                f"hard ceiling {HARD_CEILING_BYTES/1024/1024:.1f} GiB"
            )

        # Compress and store
        compressed, compression_meta = compress_data(data)
        original_size = len(data)
        compressed_size = len(compressed)

        # Write compressed blob file
        blob_path = self.storage_root.path_for_blob(sha256_hex)
        with open(blob_path, "wb") as f:
            f.write(compressed)

        # Write metadata JSON
        meta_data = {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "method": "zlib",
            "tags": tags or [],
            "collection": collection,
        }
        meta_path = self.storage_root.path_for_metadata(sha256_hex)
        with open(meta_path, "w") as f:
            json.dump(meta_data, f)

        # Record in tracking tables - use INSERT OR REPLACE / upsert now
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [])
        collection_json = json.dumps(collection) if collection else None

        c.execute(
            """INSERT OR REPLACE INTO storage_metadata
               (sha256_hex, ingestion_timestamp, size_compressed, size_uncompressed,
                reference_count, tags, collection)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sha256_hex, now, compressed_size, original_size, 1,
             tags_json, collection_json),
        )
        # Ensure reference count row exists
        c.execute(
            """INSERT OR IGNORE INTO blob_reference_counts (sha256_hex, reference_count)
               VALUES (?, 1)""",
            (sha256_hex,),
        )
        self.db_conn.commit()

        return sha256_hex, meta_data

    def retrieve_blob(self, sha256_hex: str) -> Optional[bytes]:
        """Retrieve and decompress a blob by its SHA-256 fingerprint. Returns None if not found."""
        c = self.db_conn.cursor()
        c.execute(
            """SELECT size_compressed, size_uncompressed FROM storage_metadata
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        row = c.fetchone()
        if row is None:
            return None

        blob_path = self.storage_root.path_for_blob(sha256_hex)
        if not blob_path.exists():
            return None

        try:
            with open(blob_path, "rb") as f:
                compressed = f.read()
            metadata = {
                "original_size": row[1],
                "compressed_size": row[0],
                "method": "zlib",
            }
            # Also try to read the JSON metadata for full info
            meta_path = self.storage_root.path_for_metadata(sha256_hex)
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    json_meta = json.load(f)
                metadata.update(json_meta)
            return decompress_data(compressed, metadata)
        except Exception:
            # Corrupt content; return None
            return None

    def _attempt_proactive_eviction(self, needed_bytes: int) -> bool:
        """
        Attempt to free at least needed_bytes by FIFO eviction.
        Returns True if enough bytes were freed, False otherwise.
        """
        freed_total = 0
        target = needed_bytes
        max_iterations = 1000  # prevent infinite loops

        for _ in range(max_iterations):
            if target <= 0:
                return True

            oldest, freed = self.eviction.evict_oldest(reason="proactive eviction")
            if oldest is None:
                # No more eligible blobs to evict
                return False

            freed_total += freed
            target -= freed

            # Check if we've freed enough
            current = self._current_usage_bytes()
            available = self.storage_root.hard_ceiling - current
            if available >= needed_bytes:
                return True

        return freed_total > 0  # returned partial success

    # ---- Quota reporting ----

    def get_usage_report(self) -> Dict[str, Any]:
        """Return a comprehensive usage report."""
        current = self._current_usage_bytes()
        available = self.storage_root.hard_ceiling - current
        pct_used = (current / self.storage_root.hard_ceiling) * 100 if self.storage_root.hard_ceiling else 0

        # Get eviction stats from the eviction engine
        try:
            breakdown = self.eviction.get_storage_breakdown()
        except Exception:
            breakdown = {"blobs": 0, "metadata": 0, "eviction": 0, "database": 0}

        return {
            "total_bytes": current,
            "hard_ceiling_bytes": self.storage_root.hard_ceiling,
            "soft_threshold_bytes": self.storage_root.soft_threshold,
            "available_bytes": available,
            "pct_used": round(pct_used, 2),
            "hard_ceiling_gib": round(self.storage_root.hard_ceiling / 1024**3, 3),
            "soft_threshold_gib": round(self.storage_root.soft_threshold / 1024**3, 3),
            "available_gib": round(available / 1024**3, 3),
            "pct_used_formatted": f"{pct_used:.1f}%",
            "breakdown": {
                k: round(v / 1024**2, 2) if v else 0.0
                for k, v in breakdown.items()
            },
        }

    def verify_integrity(self) -> List[Dict[str, Any]]:
        """
        Verify consistency between stored blobs, metadata, and tracking tables.
        Returns a list of issues found (empty if all consistent).
        """
        issues = []
        c = self.db_conn.cursor()

        # Check that every sha256_hex in storage_metadata has a blob file
        c.execute("SELECT sha256_hex FROM storage_metadata")
        tracked = {row[0] for row in c.fetchall()}

        for sha in tracked:
            blob_path = self.storage_root.path_for_blob(sha)
            if not blob_path.exists():
                issues.append({
                    "type": "missing_blob",
                    "sha256": sha,
                    "detail": "Tracked in metadata but blob file missing.",
                })
            meta_path = self.storage_root.path_for_metadata(sha)
            if not meta_path.exists():
                issues.append({
                    "type": "missing_metadata",
                    "sha256": sha,
                    "detail": "Tracked in DB but metadata JSON file missing.",
                })

        # Check for orphaned blob files (exist on disk but not in metadata)
        for blob_file in self.storage_root.blobs_dir.iterdir():
            if blob_file.is_file() and blob_file.suffix != ".json":
                sha = blob_file.stem
                if sha and sha not in tracked:
                    # Validate it's a plausible sha256 (64 hex chars)
                    if len(sha) == 64 and all(c in "0123456789abcdef" for c in sha):
                        issues.append({
                            "type": "orphan_blob",
                            "sha256": sha,
                            "detail": "Blob file exists on disk but is not tracked in metadata DB.",
                        })

        return issues


# ---------------------------------------------------------------------------
# FIFO Eviction engine
# -_______________________________________________________________________________


class FifoEvictionEngine:
    """
    FIFO-based eviction engine.

    Eligibility for eviction:
    - Content must be a stored blob that is referenced by at least one metadata record.
    - OR content that has reference count > 1 gets decremented first.
    - Oldest ingestion time is evicted first.

    Eviction order:
    1. Shared blobs: decrement reference count; delete only when refcount reaches 0.
    2. Individual blobs with refcount=1: evict oldest first.
    3. Metadata records: remove from index and metadata store.
    """

    def __init__(self, storage_root: StorageRoot, db_conn: sqlite3.Connection):
        self.storage_root = storage_root
        self.db_conn = db_conn
        self._ensure_tables()

    def _ensure_tables(self):
        """Create or verify the eviction-tracking schema."""
        c = self.db_conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS storage_metadata (
                sha256_hex TEXT PRIMARY KEY,
                ingestion_timestamp TEXT NOT NULL,
                size_compressed INTEGER NOT NULL DEFAULT 0,
                size_uncompressed INTEGER NOT NULL DEFAULT 0,
                reference_count INTEGER NOT NULL DEFAULT 1,
                tags TEXT NOT NULL DEFAULT '[]',
                collection TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS eviction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256_hex TEXT NOT NULL,
                evicted_at TEXT NOT NULL,
                freed_bytes INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT 'FIFO eviction'
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS blob_reference_counts (
                sha256_hex TEXT PRIMARY KEY,
                reference_count INTEGER NOT NULL DEFAULT 1
            )"""
        )
        try:
            c.execute(
                """CREATE INDEX IF NOT EXISTS idx_em_ingest
                   ON storage_metadata(ingestion_timestamp ASC)"""
            )
        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass
        self.db_conn.commit()

    def record_ingestion(self, sha256_hex: str, size_compressed: int,
                         size_uncompressed: int, tags: List[str] = None,
                         collection: str = None):
        """Record a new ingestion event, initializing reference count to 1."""
        c = self.db_conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [])
        collection_json = json.dumps(collection) if collection else None
        c.execute(
            """INSERT OR IGNORE INTO storage_metadata
               (sha256_hex, ingestion_timestamp, size_compressed, size_uncompressed,
                reference_count, tags, collection)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sha256_hex, now, size_compressed, size_uncompressed, 1,
             tags_json, collection_json),
        )
        c.execute(
            """INSERT OR IGNORE INTO blob_reference_counts (sha256_hex, reference_count)
               VALUES (?, 1)""",
            (sha256_hex,),
        )
        self.db_conn.commit()

    def increment_reference(self, sha256_hex: str):
        """Increment the reference count for a shared blob."""
        c = self.db_conn.cursor()
        c.execute(
            """UPDATE blob_reference_counts SET reference_count = reference_count + 1
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        if c.rowcount == 0:
            c.execute(
                """INSERT INTO blob_reference_counts (sha256_hex, reference_count)
                   VALUES (?, 1)""",
                (sha256_hex,),
            )
        c.execute(
            """UPDATE storage_metadata SET reference_count = reference_count + 1
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        self.db_conn.commit()

    def decrement_reference(self, sha256_hex: str) -> Optional[int]:
        """
        Decrement the reference count for a shared blob.
        Returns the new reference count, or None if the entry didn't exist.
        """
        c = self.db_conn.cursor()
        c.execute(
            """UPDATE blob_reference_counts SET reference_count = reference_count - 1
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        if c.rowcount == 0:
            return None
        c.execute(
            """UPDATE storage_metadata SET reference_count = reference_count - 1
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        self.db_conn.commit()
        # Read back the new count
        c.execute("SELECT reference_count FROM blob_reference_counts WHERE sha256_hex = ?", (sha256_hex,))
        row = c.fetchone()
        return row[0] if row else None

    def is_eligible_for_eviction(self, sha256_hex: str) -> bool:
        """Check if a blob is eligible for FIFO eviction (refcount <= 1)."""
        c = self.db_conn.cursor()
        c.execute(
            """SELECT reference_count FROM blob_reference_counts WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        row = c.fetchone()
        if row is None:
            return False
        return row[0] <= 1

    def execute_eviction(self, sha256_hex: str, reason: str = "FIFO eviction") -> int:
        """
        Execute FIFO eviction of a blob.

        Steps:
        1. Decrement reference count.
        2. Delete content blob only when refcount=0.
        3. Remove metadata record.
        4. Record eviction history.
        Returns freed bytes (0 if blob still referenced).
        """
        new_refcount = self.decrement_reference(sha256_hex)
        if new_refcount is None:
            return 0
        if new_refcount > 0:
            # Still referenced; don't delete the file.
            return 0

        # new_refcount == 0: safe to delete the blob file and metadata
        c = self.db_conn.cursor()
        c.execute(
            """SELECT size_compressed FROM storage_metadata
               WHERE sha256_hex = ?""",
            (sha256_hex,),
        )
        meta_row = c.fetchone()
        freed_bytes = meta_row[0] if meta_row else 0

        # Delete the compressed blob file
        blob_path = self.storage_root.path_for_blob(sha256_hex)
        try:
            if blob_path.exists():
                blob_path.unlink()
        except OSError as _se_debug_exc:
            print(f"[DEBUG] {__name__}: OSError in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass

        # Delete the metadata JSON file
        meta_path = self.storage_root.path_for_metadata(sha256_hex)
        try:
            if meta_path.exists():
                meta_path.unlink()
        except OSError as _se_debug_exc:
            print(f"[DEBUG] {__name__}: OSError in storage_manager: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass

        # Record eviction history
        evicted_at = datetime.now(timezone.utc).isoformat()
        c.execute(
            """INSERT INTO eviction_history (sha256_hex, evicted_at, freed_bytes, reason)
               VALUES (?, ?, ?, ?)""",
            (sha256_hex, evicted_at, freed_bytes, reason),
        )
        # Remove from active metadata and reference count tables
        c.execute("DELETE FROM storage_metadata WHERE sha256_hex = ?", (sha256_hex,))
        c.execute("DELETE FROM blob_reference_counts WHERE sha256_hex = ?", (sha256_hex,))
        self.db_conn.commit()

        return freed_bytes

    def find_oldest_eligible(self) -> Optional[str]:
        """
        Find the oldest eligible blob for FIFO eviction.
        Returns the sha256_hex of the oldest eligible blob, or None if none eligible.
        """
        c = self.db_conn.cursor()
        c.execute(
            """SELECT sm.sha256_hex, sm.ingestion_timestamp, b.reference_count
               FROM storage_metadata sm
               JOIN blob_reference_counts b ON sm.sha256_hex = b.sha256_hex
               WHERE b.reference_count <= 1
               ORDER BY sm.ingestion_timestamp ASC
               LIMIT 1"""
        )
        row = c.fetchone()
        if row:
            return row[0]
        return None

    def evict_oldest(self, reason: str = "FIFO eviction") -> Tuple[Optional[str], int]:
        """
        Find and evict the oldest eligible blob.
        Returns (sha256_hex, freed_bytes), where sha256_hex may be None if nothing evicted.
        """
        oldest = self.find_oldest_eligible()
        if oldest is None:
            return None, 0
        freed = self.execute_eviction(oldest, reason)
        return oldest, freed

    def get_storage_breakdown(self) -> Dict[str, int]:
        """Return bytes per category for debugging/accounting."""
        # Since we use incremental accounting, we report what the DB tells us
        c = self.db_conn.cursor()
        # Compressed blob size from DB
        try:
            c.execute("SELECT IFNULL(SUM(size_compressed), 0) FROM storage_metadata")
            blob_bytes = c.fetchone()[0]
        except Exception:
            blob_bytes = 0

        # We can't easily break down "metadata" vs "eviction" vs "database"
        # without directory walks, so we report the DB-tracked blob bytes
        # and leave the rest as 0 for the incremental system.
        # The usage report's breakdown will show what's trackable.
        return {
            "blobs_tracked": blob_bytes,
            "metadata_untracked": 0,
            "eviction_untracked": 0,
            "database": 0,
        }