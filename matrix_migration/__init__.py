import logging
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOGGING_LEVEL = logging.INFO
LOGGER = logging.getLogger("mami")

handler = logging.StreamHandler()
handler.setLevel(LOGGING_LEVEL)
LOGGER.setLevel(LOGGING_LEVEL)
LOGGER.addHandler(handler)
