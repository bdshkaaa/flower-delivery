"""Ручная проверка адаптера на реальном токене (не входит в CI).

    docker compose run --rm -e DELIVERY_PROVIDER=yandex backend \
        python -m app.delivery.check "Москва, Тверская 1" medium

Токен читается из YANDEX_DELIVERY_TOKEN (файл .env) и нигде не печатается."""
import sys

from ..config import settings
from .base import Destination, ProviderError
from .factory import get_provider


def main() -> int:
    address = sys.argv[1] if len(sys.argv) > 1 else "Москва, Тверская 1"
    weight = sys.argv[2] if len(sys.argv) > 2 else "medium"
    print(f"provider={settings.delivery_provider} address={address!r} weight={weight}")
    try:
        quote = get_provider(settings).get_quote(Destination(region_key="check", address=address), weight)
    except (ProviderError, ValueError) as exc:
        print(f"ОШИБКА: {exc}")
        return 1
    print(f"OK: стоимость {quote.cost} ₽, срок {quote.eta_days} дн.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
