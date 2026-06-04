"""Скачать и сохранить тарифы ProxyAPI в proxyapi_pricing.json."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.proxyapi_pricing import ProxyApiPricingStore  # noqa: E402


async def main() -> None:
    store = ProxyApiPricingStore(ROOT / "proxyapi_pricing.json")
    payload = await store.refresh_from_site()
    models = payload.get("models", {})
    print(f"OK: {len(models)} models -> {store._path}")
    for model_id in ("gpt-5.4-mini", "gpt-image-2", "gpt-5.5"):
        rates = models.get(model_id)
        if rates:
            print(model_id, rates)


if __name__ == "__main__":
    asyncio.run(main())
