import json
from datetime import UTC, datetime

import httpx

from ratatosk.core.config import settings
from ratatosk.core.dynamic_settings import dynamic_settings


class CurrencyManager:
    def __init__(self):
        self.dictionary = self.load_converter_reference()
        self.next_update = datetime.fromtimestamp(
            self.dictionary["time_next_update_unix"], tz=UTC
        )

    def _refresh(self):
        try:
            self.dictionary = self.load_converter_reference(force_update=True)
            self.next_update = datetime.fromtimestamp(
                self.dictionary["time_next_update_unix"], tz=UTC
            )
        except Exception:  # noqa: S110, BLE001 : if refresh doesn't work, it will be ignored
            pass

    def convert(self, price_usd: float, currency: str) -> float:
        if datetime.now(UTC) >= self.next_update:
            self._refresh()
        rate = self.dictionary["rates"][currency.upper()]
        return price_usd * rate

    def auto_convert(self, price_usd: float) -> float:
        return self.convert(price_usd, dynamic_settings.currency)

    def load_converter_reference(self, force_update: bool = False) -> dict:
        cache_file = settings.app_dir / "ExchangeRate.json"

        if cache_file.exists() and not force_update:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                next_update = datetime.fromtimestamp(
                    cached_data["time_next_update_unix"], tz=UTC
                )
                if datetime.now(UTC) < next_update:
                    return cached_data
            except (ValueError, KeyError, OSError):
                pass

        try:
            response = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=10.0)
            response.raise_for_status()
            data = response.json()

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            return data

        except (httpx.HTTPError, ValueError, OSError) as e:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise RuntimeError(f"Failed to fetch currency dictionary: {e}")


currency_manager = CurrencyManager()
