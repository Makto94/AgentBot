"""Backend settings from environment."""

import os


DATABASE_URL = (
    f"postgresql://{os.environ.get('POSTGRES_USER', 'scanner')}"
    f":{os.environ.get('POSTGRES_PASSWORD', 'scanner_password')}"
    f"@{os.environ.get('POSTGRES_HOST', 'stock_scanner_db')}"
    f":{os.environ.get('POSTGRES_PORT', '5432')}"
    f"/{os.environ.get('POSTGRES_DB', 'stock_scanner')}"
)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://stock-scanner.tomd.space").split(",")
