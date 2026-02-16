import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "recon.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes the database schema."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scan_id TEXT,
                        target TEXT NOT NULL,
                        module TEXT NOT NULL,
                        source TEXT NOT NULL,
                        type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Try to add scan_id column if it doesn't exist (for existing DBs)
                try:
                    conn.execute("ALTER TABLE results ADD COLUMN scan_id TEXT")
                except sqlite3.OperationalError:
                    pass # Already exists

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scans (
                        id TEXT PRIMARY KEY,
                        target TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time DATETIME,
                        end_time DATETIME
                    )
                """)
                # Create index for faster lookups
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_target ON results(target)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_scan_id ON results(scan_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_type ON results(type)")
                conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def store_result(self, target: str, module: str, source: str, result_type: str, data: Any, scan_id: Optional[str] = None):
        """Stores a result in the database. Data is JSON serialized."""
        try:
            logger.debug(f"[DB DEBUG] Attempting to store result: Target={target}, Module={module}, Type={result_type}, ScanID={scan_id}")
            serialized_data = json.dumps(data)
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO results (scan_id, target, module, source, type, data) VALUES (?, ?, ?, ?, ?, ?)",
                    (scan_id, target, module, source, result_type, serialized_data)
                )
                conn.commit()
            logger.debug(f"[DB DEBUG] Successfully stored {result_type} result. Data size: {len(serialized_data)} bytes")
        except sqlite3.Error as e:
            logger.error(f"Failed to store result in DB: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def get_results(self, target: str, module: Optional[str] = None, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves results for a target or scan_id, optionally filtered by module."""
        results = []
        try:
            if scan_id:
                query = "SELECT id, target, module, source, type, data, timestamp, scan_id FROM results WHERE scan_id = ?"
                params = [scan_id]
            else:
                query = "SELECT id, target, module, source, type, data, timestamp, scan_id FROM results WHERE target = ?"
                params = [target]
            
            if module:
                if "/" in module:
                    query += " AND module = ?"
                else:
                    query += " AND module LIKE ?"
                    module = f"{module}/%"
                params.append(module)

            logger.debug(f"[DB DEBUG] Executing query: {query} with params: {params}")
            with self._get_connection() as conn:
                cursor = conn.execute(query, tuple(params))
                for row in cursor:
                    results.append({
                        "id": row[0],
                        "target": row[1],
                        "module": row[2],
                        "source": row[3],
                        "type": row[4],
                        "data": json.loads(row[5]),
                        "timestamp": row[6],
                        "scan_id": row[7]
                    })
            logger.debug(f"[DB DEBUG] Retrieved {len(results)} results")
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve results from DB: {e}")
        
        return results

    def get_unique_subdomains(self, target: str) -> List[str]:
        """Returns a deduplicated list of unique subdomains found for a target."""
        results = self.get_results(target, module="subdomain")
        subdomains = set()
        for res in results:
            if isinstance(res['data'], list):
                for item in res['data']:
                    if 'subdomain' in item:
                        subdomains.add(item['subdomain'])
        return sorted(list(subdomains))

    def get_unique_results(self, target: str, result_type: str, key_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Aggregates and deduplicates results by result_type across all sources."""
        results = self.get_results(target)
        unique = []
        seen = set()

        for res in results:
            if res.get("type") != result_type:
                continue
            data = res.get("data")
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if key_fields:
                    key = tuple(entry.get(field) for field in key_fields)
                else:
                    key = json.dumps(entry, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                unique.append(entry)

        return unique

    def deduplicate_results(self, target: str, result_type: Optional[str] = None) -> int:
        """Removes duplicate rows for a target (optionally by type) based on data content."""
        try:
            with self._get_connection() as conn:
                if result_type:
                    query = "SELECT id, type, data FROM results WHERE target = ? AND type = ?"
                    rows = conn.execute(query, (target, result_type)).fetchall()
                else:
                    query = "SELECT id, type, data FROM results WHERE target = ?"
                    rows = conn.execute(query, (target,)).fetchall()

                seen = set()
                to_delete = []

                for row_id, r_type, data in rows:
                    key = (r_type, data)
                    if key in seen:
                        to_delete.append((row_id,))
                    else:
                        seen.add(key)

                if to_delete:
                    conn.executemany("DELETE FROM results WHERE id = ?", to_delete)
                    conn.commit()
                return len(to_delete)
        except sqlite3.Error as e:
            logger.error(f"Failed to deduplicate results: {e}")
            return 0

    def create_scan(self, scan_id: str, target: str, status: str = "pending"):
        """Creates a new scan record."""
        try:
            logger.debug(f"[DB DEBUG] Creating scan record: ID={scan_id}, Target={target}, Status={status}")
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO scans (id, target, status, start_time) VALUES (?, ?, ?, ?)",
                    (scan_id, target, status, datetime.now())
                )
                conn.commit()
            logger.debug(f"[DB DEBUG] Scan record created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create scan: {e}")

    def update_scan_status(self, scan_id: str, status: str):
        """Updates the status of a scan."""
        try:
            logger.debug(f"[DB DEBUG] Updating scan status: ID={scan_id}, New Status={status}")
            with self._get_connection() as conn:
                if status in ["completed", "failed", "stopped"]:
                    conn.execute(
                        "UPDATE scans SET status = ?, end_time = ? WHERE id = ?",
                        (status, datetime.now(), scan_id)
                    )
                else:
                    conn.execute(
                        "UPDATE scans SET status = ? WHERE id = ?",
                        (status, scan_id)
                    )
                conn.commit()
            logger.debug(f"[DB DEBUG] Scan status updated successfully to {status}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update scan status: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single scan by ID."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT id, target, status, start_time, end_time FROM scans WHERE id = ?",
                    (scan_id,)
                ).fetchone()
                if row:
                    return {
                        "id": row[0],
                        "target": row[1],
                        "status": row[2],
                        "start_time": row[3],
                        "end_time": row[4]
                    }
        except sqlite3.Error as e:
            logger.error(f"Failed to get scan: {e}")
        return None

    def get_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent scans."""
        scans = []
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, target, status, start_time, end_time FROM scans ORDER BY start_time DESC LIMIT ?",
                    (limit,)
                )
                for row in cursor:
                    scans.append({
                        "id": row[0],
                        "target": row[1],
                        "status": row[2],
                        "start_time": row[3],
                        "end_time": row[4]
                    })
        except sqlite3.Error as e:
            logger.error(f"Failed to get scans: {e}")
        return scans
    def clear_history(self):
        """Clears all scan and result history from the database."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM results")
                conn.execute("DELETE FROM scans")
                conn.commit()
            logger.info("Database history cleared successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear history: {e}")
            raise
