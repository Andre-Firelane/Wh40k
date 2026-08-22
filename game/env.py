import os

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def load_dotenv():
    """Minimal .env loader (KEY=value per line, '#' comments) - avoids adding
    the python-dotenv dependency for a single secret. Only fills in keys not
    already set in the real environment, so an explicit `export`/`$env:`
    always wins over the file."""
    if not os.path.isfile(_ENV_PATH):
        return
    with open(_ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
