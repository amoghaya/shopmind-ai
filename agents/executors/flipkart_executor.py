from agents.executors.base import BaseExecutor, ExecutionRequest, ExecutionResult


class FlipkartExecutor(BaseExecutor):
    name = "flipkart"
    mode = "experimental"

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            executor_name=self.name,
            success=False,
            steps=[{"action": "blocked", "reason": "experimental adapter not enabled in reproducible benchmark mode"}],
            latency_ms=0,
            failure_category="experimental_adapter_disabled",
        )

