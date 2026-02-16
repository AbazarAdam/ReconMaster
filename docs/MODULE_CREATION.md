# ReconMaster: Module Creation Guide

This guide explains how to create and integrate new reconnaissance modules into the ReconMaster framework.

## 🧱 Module Architecture

All modules in ReconMaster must inherit from `core.module_loader.BaseModule`. This base class provides essential infrastructure, including:

- **Config Access**: `self.config`
- **Database Access**: `self.db`
- **Rate Limiting**: `self.limiter`
- **Proxy Management**: `self.proxy_manager`
- **Deduplication**: `self.store_results()`

## 🛠️ Step-by-Step Implementation

### 1. Create the File
Place your new module in a subdirectory under `modules/` (e.g., `modules/subdomain/my_source.py`).

### 2. Define the Class
```python
import logging
from typing import List, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class MySourceModule(BaseModule):
    """Provides a brief description of what the module does."""

    @property
    def name(self) -> str:
        """The logical name used in configurations and database logs."""
        return "my_source"

    @property
    def module_type(self) -> str:
        """The category (e.g., 'subdomain', 'enum', 'vuln')."""
        return "subdomain"

    async def run(self, target: str) -> None:
        """Main entry point for the module's logic."""
        logger.info(f"Starting MySource discovery for {target}")
        
        # 1. Respect Rate Limits
        if self.limiter:
            await self.limiter.acquire()

        try:
            # 2. Perform Discovery (Example)
            # results = await self.my_api_call(target, proxy=self.get_request_proxy())
            findings = [{"subdomain": f"dev.{target}", "source": self.name}]
            
            # 3. Store Results
            if findings:
                self.store_results(target, self.name, "subdomain", findings)
                logger.info(f"Found {len(findings)} results")
                
        except Exception as e:
            logger.error(f"Module failed: {e}")
```

### 3. Guidelines & Best Practices

-   **Type Hinting**: Always provide type hints for function arguments and return values.
-   **Logging**: Use `logger.info()` for significant events and `logger.debug()` for verbose details. Never use `print()`.
-   **Error Handling**: Wrap your logic in `try/except` blocks to ensure a single module failure doesn't crash the entire scan.
-   **Async First**: Use `aiohttp` for networking. If using a synchronous library, offload it to a thread using `asyncio.to_thread`.
-   **Respect Proxies**: Always use `self.get_request_proxy()` for external network requests.

## ⚙️ Registration

Once implemented, enable your module in `config/default.yaml`:

```yaml
modules:
  enabled:
    subdomain:
      - "ct"
      - "my_source"  # Add your module name here
```

The engine will automatically load and execute your module during the next scan.
