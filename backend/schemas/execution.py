from pydantic import BaseModel, Field


class ExecutionIntent(BaseModel):
    session_id: str
    query: str
    category: str | None = None
    filters: dict = Field(default_factory=dict)
    product_id: int | None = None


class ExecutionRunRead(BaseModel):
    run_id: str
    session_id: str
    executor_name: str
    status: str
    steps: list[dict]
    screenshot_paths: list[str]
    screenshot_urls: list[str] = []
    failure_category: str | None = None
    latency_ms: int | None = None
