import importlib
import inspect
import logging
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Type, Optional

logger = logging.getLogger(__name__)

class BaseModule(ABC):
    def __init__(self, config: Dict[str, Any], database: Any, scan_id: Optional[str] = None, rate_limiter: Any = None, proxy_manager: Any = None):
        self.config = config
        self.db = database
        self.scan_id = scan_id
        self.limiter = rate_limiter
        self.proxy = proxy_manager

    def get_session_kwargs(self) -> Dict[str, Any]:
        """
        Returns arguments for aiohttp.ClientSession and request methods.
        """
        kwargs = {}
        if self.proxy:
            connector = self.proxy.get_connector()
            if connector:
                kwargs["connector"] = connector
            
            # For HTTP proxies, we might need to pass the 'proxy' arg to request methods
            # but we'll provide a helper for that too.
        return kwargs

    def get_request_proxy(self) -> Optional[str]:
        """Returns proxy URL for request methods if applicable."""
        return self.proxy.get_proxy_url() if self.proxy else None

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the module."""
        pass

    @property
    @abstractmethod
    def module_type(self) -> str:
        """Type of the module (e.g., 'subdomain', 'portscan')."""
        pass

    @abstractmethod
    async def run(self, target: str):
        """Main entry point for the module's logic."""
        pass

    def validate_target(self, target: str) -> bool:
        """Basic validation for the target domain."""
        # Very simple validation for now, can be expanded
        return "." in target and len(target) > 3

    def store_results(self, target: str, source: str, result_type_or_data: Any, data: Any = None):
        """
        Convenience method to store results in the database.
        Supports both:
          - store_results(target, source, result_type, data)
          - store_results(target, source, data) -> uses self.module_type as result_type
        """
        if data is None:
            # Shift arguments: result_type_or_data IS the data, type is module_type
            actual_data = result_type_or_data
            actual_type = self.module_type
        else:
            actual_data = data
            actual_type = result_type_or_data

        logger.debug(f"[MODULE DEBUG] {self.module_type}/{self.name} storing {len(actual_data) if isinstance(actual_data, list) else 1} findings for {target} (Scan: {self.scan_id})")

        self.db.store_result(
            target=target,
            module=f"{self.module_type}/{self.name}",
            source=source,
            result_type=actual_type,
            data=actual_data,
            scan_id=self.scan_id
        )

class ModuleLoader:
    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = Path(modules_dir)

    async def load_enabled_modules(self, config: Dict[str, Any], db: Any, scan_id: Optional[str] = None, rate_limiter: Any = None, proxy_manager: Any = None) -> List[BaseModule]:
        """
        Loads modules based on the configuration.
        """
        enabled_config = config.get("modules", {}).get("enabled", {})
        loaded_modules = []
        
        for m_type, sources in enabled_config.items():
            m_type_path = self.modules_dir / m_type
            if not m_type_path.exists():
                logger.warning(f"Module type directory {m_type_path} not found.")
                continue

            for source in sources:
                module_path = f"modules.{m_type}.{source}"
                try:
                    full_module = importlib.import_module(module_path)
                    
                    found_classes = [
                        obj for name, obj in inspect.getmembers(full_module)
                        if inspect.isclass(obj) and issubclass(obj, BaseModule) and obj is not BaseModule
                    ]

                    for cls in found_classes:
                        # Get module-specific config and merge with API keys
                        module_cfg = config.get("modules", {}).get(m_type, {}).copy()
                        module_cfg["api_keys"] = config.get("api_keys", {})
                        
                        instance = cls(module_cfg, db, scan_id=scan_id, rate_limiter=rate_limiter, proxy_manager=proxy_manager)
                        loaded_modules.append(instance)
                        logger.debug(f"Loaded module: {m_type}/{source} for scan {scan_id}")
                
                except Exception as e:
                    logger.error(f"Failed to load module {module_path}: {e}")

        return loaded_modules
