import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Логирование в STDOUT (требование этапа 4 задания)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
