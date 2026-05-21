from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "api_requests_total",
    "API request count",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency",
    ["method", "path"],
)
RECOMMENDATION_COUNT = Counter(
    "recommendation_requests_total",
    "Recommendation requests by strategy",
    ["strategy"],
)
EXECUTION_FAILURE_COUNT = Counter(
    "execution_failures_total",
    "Execution failures by category",
    ["category"],
)
EXECUTION_COUNT = Counter(
    "execution_runs_total",
    "Execution runs by executor and outcome",
    ["executor", "outcome"],
)
EXECUTION_LATENCY = Histogram(
    "execution_latency_seconds",
    "Execution latency by executor",
    ["executor"],
)
TASK_SUCCESS_RATE = Gauge(
    "task_success_rate",
    "Rolling execution task success rate",
)
REGRET_GAUGE = Gauge(
    "recommendation_cumulative_regret",
    "Cumulative recommendation regret",
)
