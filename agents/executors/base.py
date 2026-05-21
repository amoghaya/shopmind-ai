from dataclasses import dataclass, field


@dataclass
class ExecutionRequest:
    session_id: str
    query: str
    category: str | None = None
    filters: dict = field(default_factory=dict)
    checkout_approved: bool = False
    product_id: int | None = None
    run_id: str | None = None


@dataclass
class ExecutionResult:
    executor_name: str
    success: bool
    steps: list[dict]
    latency_ms: int
    screenshot_paths: list[str] = field(default_factory=list)
    failure_category: str | None = None


class BaseExecutor:
    name = "base"
    mode = "experimental"

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError
