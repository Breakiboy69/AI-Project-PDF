import os
from .config import TXT_DIR, OUTPUT_DIR


def ensure_dirs():
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

