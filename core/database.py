import json
import logging
import sqlite3
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Database:
    """Handles all synchronous interactions with the SQLite database.

    Attributes:
        db_path: The filesystem path to the SQLite database file.
    """

    def __init__(self, db_path: str = "recon.db"):
        """Initializes the Database instance and ensures the schema is ready.

        Args:
            db_path: Path to the database file. Defaults to "recon.db".
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates and returns a new SQLite connection.

        Returns:
            A sqlite3.Connection object.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initializes the database schema if tables do not exist.

        Sets up 'results' and 'scans' tables and creates necessary indexes.
        """
        try:
            with self._get_connection() as conn:
                # Results table for module findings
                conn.execute(
                    """
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
                """
                )

                # Schema migration for existing databases
                try:
                    conn.execute("ALTER TABLE results ADD COLUMN scan_id TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists

                # Scans table for tracking execution state
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scans (
                        id TEXT PRIMARY KEY,
                        target TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time DATETIME,
                        end_time DATETIME
                    )
                """
                )

                # Indexes for performance optimization
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_target ON results(target)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_scan_id ON results(scan_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_results_type ON results(type)")
                conn.commit()

            logger.info(f"Database initialized and schema verified at {self.db_path}")
        except sqlite3.Error as e:
            logger.critical(f"Failed to initialize database at {self.db_path}: {e}")
            raise

    def store_result(
        self,
        target: str,
        module: str,
        source: str,
        result_type: str,
        data: Any,
        scan_id: Optional[str] = None,
    ) -> None:
        """Stores a module result in the database.

        Args:
            target: The target domain or IP.
            module: The name of the module that generated the result.
            source: The specific source or tool within the module.
            result_type: The category of the result (e.g., 'subdomain', 'http').
            data: The actual finding data (will be JSON serialized).
            scan_id: Optional UUID linking the result to a specific scan session.
        """
        try:
            logger.debug(
                f"[DB] Storing {result_type} result | Target: {target} | Module: {module} | ScanID: {scan_id}"
            )
            serialized_data = json.dumps(data)
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO results (scan_id, target, module, source, type, data) VALUES (?, ?, ?, ?, ?, ?)",
                    (scan_id, target, module, source, result_type, serialized_data),
                )
                conn.commit()
            logger.debug(f"[DB] Successfully stored {result_type} result ({len(serialized_data)} bytes)")
        except sqlite3.Error as e:
            logger.error(f"Failed to store result in database: {e}")
            logger.debug(traceback.format_exc())

    def get_results(
        self, target: str, module: Optional[str] = None, scan_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves results filtered by target, scan_id, or module.

        Args:
            target: The target to filter by.
            module: Optional module name filter.
            scan_id: Optional scan ID filter.

        Returns:
            A list of dictionary results with deserialized data.
        """
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

            logger.debug(f"[DB] Executing result query for target: {target}")
            with self._get_connection() as conn:
                cursor = conn.execute(query, tuple(params))
                for row in cursor:
                    results.append(
                        {
                            "id": row[0],
                            "target": row[1],
                            "module": row[2],
                            "source": row[3],
                            "type": row[4],
                            "data": json.loads(row[5]),
                            "timestamp": row[6],
                            "scan_id": row[7],
                        }
                    )
            logger.debug(f"[DB] Retrieved {len(results)} results")
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve results from database: {e}")

        return results

    def get_unique_subdomains(self, target: str) -> List[str]:
        """Returns a deduplicated and sorted list of unique subdomains for a target.

        Args:
            target: The root domain to search for.

        Returns:
            A list of unique subdomain strings.
        """
        results = self.get_results(target, module="subdomain")
        subdomains = set()
        for res in results:
            data = res.get("data", [])
            entries = data if isinstance(data, list) else [data]
            for item in entries:
                if isinstance(item, dict) and "subdomain" in item:
                    subdomains.add(item["subdomain"])
        return sorted(list(subdomains))

    def get_unique_results(
        self, target: str, result_type: str, key_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Aggregates and deduplicates results by type across all sources.

        Args:
            target: The target to filter by.
            result_type: The type of results to aggregate.
            key_fields: Optional list of fields to used for uniqueness calculation.
                If omitted, the entire data object is used.

        Returns:
            A list of unique findings.
        """
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
        """Physically removes duplicate rows from the database for a given target.

        Args:
            target: The target whose results should be cleaned.
            result_type: Optional filter to only deduplicate specific result types.

        Returns:
            The number of duplicate rows deleted.
        """
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
            logger.error(f"Failed to deduplicate database rows: {e}")
            return 0

    def create_scan(self, scan_id: str, target: str, status: str = "pending") -> None:
        """Initializes a new scan entry in the tracking table.

        Args:
            scan_id: The unique identifier for the scan.
            target: The target domain or host.
            status: Initial status of the scan. Defaults to "pending".
        """
        try:
            logger.info(f"[DB] Creating scan tracking entry | ID: {scan_id} | Target: {target}")
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO scans (id, target, status, start_time) VALUES (?, ?, ?, ?)",
                    (scan_id, target, status, datetime.now()),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create scan record: {e}")

    def update_scan_status(self, scan_id: str, status: str) -> None:
        """Updates the progress status and timing for an active scan.

        Args:
            scan_id: The ID of the scan to update.
            status: The new status string (e.g., 'running', 'completed').
        """
        try:
            logger.debug(f"[DB] Updating scan status | ID: {scan_id} | Status: {status}")
            with self._get_connection() as conn:
                if status in ["completed", "failed", "stopped"]:
                    conn.execute(
                        "UPDATE scans SET status = ?, end_time = ? WHERE id = ?",
                        (status, datetime.now(), scan_id),
                    )
                else:
                    conn.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update scan status for {scan_id}: {e}")
            logger.debug(traceback.format_exc())

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific scan record by its ID.

        Args:
            scan_id: The UUID of the scan.

        Returns:
            The scan record as a dictionary or None if not found.
        """
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT id, target, status, start_time, end_time FROM scans WHERE id = ?",
                    (scan_id,),
                ).fetchone()
                if row:
                    return {
                        "id": row[0],
                        "target": row[1],
                        "status": row[2],
                        "start_time": row[3],
                        "end_time": row[4],
                    }
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve scan {scan_id}: {e}")
        return None

    def get_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves a list of recent scan records.

        Args:
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            A list of scan record dictionaries.
        """
        scans = []
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, target, status, start_time, end_time FROM scans ORDER BY start_time DESC LIMIT ?",
                    (limit,),
                )
                for row in cursor:
                    scans.append(
                        {
                            "id": row[0],
                            "target": row[1],
                            "status": row[2],
                            "start_time": row[3],
                            "end_time": row[4],
                        }
                    )
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve scan history: {e}")
        return scans

    def clear_history(self) -> None:
        """Wipes all data from both results and scans tables. Use with caution."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM results")
                conn.execute("DELETE FROM scans")
                conn.commit()
            logger.warning("All database history has been cleared.")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear database history: {e}")
            raise
