import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """Abstract base class for all reconnaissance modules.

    Provides common infrastructure for logging, result storage, and
    utility methods for interacting with proxies and rate limiters.

    Attributes:
        config: Module-specific configuration dictionary.
        db: Reference to the database handler.
        scan_id: UUID of the current scan session.
        limiter: Reference to the rate limiter instance.
        proxy: Reference to the proxy manager instance.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database: Any,
        scan_id: Optional[str] = None,
        rate_limiter: Any = None,
        proxy_manager: Any = None,
    ):
        """Initializes the base module with shared infrastructure.

        Args:
            config: A dictionary containing module settings.
            database: An initialized Database instance.
            scan_id: Optional scan ID for session tracking.
            rate_limiter: Optional RateLimiter instance.
            proxy_manager: Optional ProxyManager instance.
        """
        self.config = config
        self.db = database
        self.scan_id = scan_id
        self.limiter = rate_limiter
        self.proxy = proxy_manager

    def get_session_kwargs(self) -> Dict[str, Any]:
        """Provides keyword arguments for aiohttp.ClientSession initialization.

        Returns:
            A dictionary containing session parameters like 'connector'.
        """
        kwargs = {}
        if self.proxy:
            connector = self.proxy.get_connector()
            if connector:
                kwargs["connector"] = connector
        return kwargs

    def get_request_proxy(self) -> Optional[str]:
        """Retrieves the current proxy URL for low-level request methods.

        Returns:
            The proxy URL as a string (e.g., 'http://127.0.0.1:8080') or None.
        """
        return self.proxy.get_proxy_url() if self.proxy else None

    @property
    @abstractmethod
    def name(self) -> str:
        """The specific name of the module (e.g., 'crtsh')."""
        pass

    @property
    @abstractmethod
    def module_type(self) -> str:
        """The category of the module (e.g., 'subdomain')."""
        pass

    @abstractmethod
    async def run(self, target: str) -> None:
        """Main execution logic for the module. Must be implemented by subclasses.

        Args:
            target: The domain or host to process.
        """
        pass

    def validate_target(self, target: str) -> bool:
        """Performs basic heuristic validation of the target string.

        Args:
            target: The host string to validate.

        Returns:
            True if the target appears valid, False otherwise.
        """
        return "." in target and len(target) > 3

    def store_results(
        self, target: str, source: str, result_type_or_data: Any, data: Any = None
    ) -> None:
        """Helper method to store findings in the database with consistent metadata.

        Args:
            target: The host discovery was made on.
            source: The specific tool/API source (e.g., 'VirusTotal').
            result_type_or_data: Either the result category (string) OR the data object.
            data: If provided, result_type_or_data is treated as the category.
        """
        if data is None:
            # Polymorphic behavior: if data is omitted, treat type_or_data as the data
            actual_data = result_type_or_data
            actual_type = self.module_type
        else:
            actual_data = data
            actual_type = result_type_or_data

        log_count = len(actual_data) if isinstance(actual_data, (list, dict)) else 1
        logger.debug(
            f"[MODULE] {self.module_type}/{self.name} storing {log_count} finding(s) | Scan: {self.scan_id}"
        )

        self.db.store_result(
            target=target,
            module=f"{self.module_type}/{self.name}",
            source=source,
            result_type=actual_type,
            data=actual_data,
            scan_id=self.scan_id,
        )


class ModuleLoader:
    """Dynamically locates and instantiates reconnaissance modules.

    Attributes:
        modules_dir: The root filesystem directory containing module packages.
    """

    def __init__(self, modules_dir: str = "modules"):
        """Initializes the loader with a target directory.

        Args:
            modules_dir: Path to the modules folder. Defaults to "modules".
        """
        self.modules_dir = Path(modules_dir)

    async def load_enabled_modules(
        self,
        config: Dict[str, Any],
        db: Any,
        scan_id: Optional[str] = None,
        rate_limiter: Any = None,
        proxy_manager: Any = None,
    ) -> List[BaseModule]:
        """Scans the module directory and loads classes enabled in the config.

        Args:
            config: The root or partial application configuration.
            db: Initialized Database instance.
            scan_id: Optional UUID of the scan session.
            rate_limiter: Reference to the shared RateLimiter.
            proxy_manager: Reference to the shared ProxyManager.

        Returns:
            A list of instantiated module objects ready for execution.
        """
        enabled_config = config.get("modules", {}).get("enabled", {})
        loaded_modules = []

        for m_type, sources in enabled_config.items():
            m_type_path = self.modules_dir / m_type
            if not m_type_path.exists():
                logger.warning(f"Module type directory not found: {m_type_path}")
                continue

            for source in sources:
                module_path = f"modules.{m_type}.{source}"
                try:
                    full_module = importlib.import_module(module_path)

                    # Identify all classes that inherit from BaseModule (excluding BaseModule itself)
                    found_classes = [
                        obj
                        for _, obj in inspect.getmembers(full_module)
                        if inspect.isclass(obj)
                        and issubclass(obj, BaseModule)
                        and obj is not BaseModule
                    ]

                    for cls in found_classes:
                        # Prepare module-specific config overlay
                        module_cfg = config.get("modules", {}).get(m_type, {}).copy()
                        module_cfg["api_keys"] = config.get("api_keys", {})

                        instance = cls(
                            module_cfg,
                            db,
                            scan_id=scan_id,
                            rate_limiter=rate_limiter,
                            proxy_manager=proxy_manager,
                        )
                        loaded_modules.append(instance)
                        logger.debug(
                            f"[LOADER] Loaded {m_type}/{source} (ID: {scan_id})"
                        )

                except ImportError as e:
                    logger.error(f"Failed to import module {module_path}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading module {module_path}: {e}")

        return loaded_modules
