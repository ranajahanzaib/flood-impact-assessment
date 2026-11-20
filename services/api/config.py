from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Flood Impact Assessment"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Storage paths
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"
    UPLOADS_DIR: Path = PROJECT_ROOT / "data" / "uploads"
    PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
    EXPORTS_DIR: Path = PROJECT_ROOT / "data" / "exports"

    # Database
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT}/data/flood_impact.db"

    # Processing Defaults
    DEFAULT_TILE_SIZE: int = 512
    DEFAULT_INFERENCE_BATCH_SIZE: int = 4
    MAX_UPLOAD_SIZE_MB: int = 500

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Ensure directories exist
for d in [
    settings.DATA_DIR,
    settings.CACHE_DIR,
    settings.UPLOADS_DIR,
    settings.PROCESSED_DIR,
    settings.EXPORTS_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)
