from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="HNB Shopping Avatar", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(default="sqlite:///./shopmind.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://redis:6379/2",
        alias="CELERY_RESULT_BACKEND",
    )
    mlflow_tracking_uri: str = Field(
        default="http://mlflow:5000",
        alias="MLFLOW_TRACKING_URI",
    )
    model_registry_path: str = Field(default="artifacts/models", alias="MODEL_REGISTRY_PATH")
    dataset_root: str = Field(default="datasets", alias="DATASET_ROOT")
    use_mock_recommender: bool = Field(default=True, alias="USE_MOCK_RECOMMENDER")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    shopsim_base_url: str = Field(default="http://localhost:5173", alias="SHOPSIM_BASE_URL")
    execution_artifacts_dir: str = Field(
        default="artifacts/executions",
        alias="EXECUTION_ARTIFACTS_DIR",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
