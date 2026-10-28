"""Ручная проверка служб доставки на реальных ключах (не входит в CI).

    docker compose run --rm -e DELIVERY_PROVIDERS=courier,yandex,cdek backend \
        python -m app.delivery.check "Москва, Тверская 1" medium

Ключи читаются из .env (YANDEX_DELIVERY_TOKEN, CDEK_CLIENT_ID, CDEK_CLIENT_SECRET)
и нигде не печатаются. Для каждой службы выводятся её варианты или причина отказа."""
import sys

from ..config import settings
from .base import BadAddressError, Destination, NotServiceable, ProviderError
from .factory import build_providers


def main() -> int:
    address = sys.argv[1] if len(sys.argv) > 1 else "Москва, Тверская 1"
    weight = sys.argv[2] if len(sys.argv) > 2 else "medium"
    print(f"providers={settings.delivery_providers} address={address!r} weight={weight}")
    failed = 0
    for provider in build_providers(settings):
        try:
            options = provider.get_options(Destination(region_key="check", address=address), weight)
        except NotServiceable as exc:
            print(f"[{provider.id}] не доставляет: {exc.reason}")
        except (BadAddressError, ProviderError, ValueError) as exc:
            print(f"[{provider.id}] ОШИБКА: {exc}")
            failed += 1
        else:
            for o in options:
                print(f"[{provider.id}] {o.service}: {o.cost} ₽, срок {o.eta_days} дн.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
