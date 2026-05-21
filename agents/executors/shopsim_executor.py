import asyncio
import time
from pathlib import Path
from typing import Callable

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from agents.executors.base import BaseExecutor, ExecutionRequest, ExecutionResult


class ShopSimExecutor(BaseExecutor):
    name = "shopsim"
    mode = "primary"
    session_storage_key = "shopsim-session-id"

    def __init__(
        self,
        base_url: str,
        artifacts_dir: str,
        headless: bool = True,
        progress_hook: Callable[..., None] | None = None,
        step_delay_s: float = 0.9,
        run_timeout_s: float = 35.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.artifacts_dir = Path(artifacts_dir)
        self.headless = headless
        self.progress_hook = progress_hook
        self.step_delay_s = step_delay_s
        self.run_timeout_s = run_timeout_s

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.perf_counter()
        run_dir = self.artifacts_dir / (request.run_id or f"exec-{int(started)}")
        run_dir.mkdir(parents=True, exist_ok=True)
        screenshots: list[str] = []
        steps: list[dict] = []
        self._notify("running", steps, screenshots, None, None)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless, slow_mo=250)
            context = await browser.new_context()
            await context.add_init_script(
                """
                (payload) => {
                  window.localStorage.setItem(payload.key, payload.value);
                }
                """,
                {"key": self.session_storage_key, "value": request.session_id},
            )
            page = await context.new_page()
            try:
                flow_result = await asyncio.wait_for(
                    self._run_flow(page, browser, request, steps, screenshots, started),
                    timeout=self.run_timeout_s,
                )
                if flow_result == "paused":
                    return ExecutionResult(
                        executor_name=self.name,
                        success=True,
                        steps=steps,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        screenshot_paths=screenshots,
                    )
            except asyncio.TimeoutError:
                await browser.close()
                latency_ms = int((time.perf_counter() - started) * 1000)
                if steps:
                    steps[-1]["status"] = "timeout"
                self._notify("failed", steps, screenshots, "timeout", latency_ms)
                return ExecutionResult(
                    executor_name=self.name,
                    success=False,
                    steps=steps,
                    latency_ms=latency_ms,
                    screenshot_paths=screenshots,
                    failure_category="timeout",
                )
            except PlaywrightTimeoutError:
                await browser.close()
                latency_ms = int((time.perf_counter() - started) * 1000)
                self._notify("failed", steps, screenshots, "timeout", latency_ms)
                return ExecutionResult(
                    executor_name=self.name,
                    success=False,
                    steps=steps,
                    latency_ms=latency_ms,
                    screenshot_paths=screenshots,
                    failure_category="timeout",
                )
            except Exception:
                await browser.close()
                latency_ms = int((time.perf_counter() - started) * 1000)
                self._notify("failed", steps, screenshots, "execution_error", latency_ms)
                return ExecutionResult(
                    executor_name=self.name,
                    success=False,
                    steps=steps,
                    latency_ms=latency_ms,
                    screenshot_paths=screenshots,
                    failure_category="execution_error",
                )

            await browser.close()
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._notify("success", steps, screenshots, None, latency_ms)
        return ExecutionResult(
            executor_name=self.name,
            success=True,
            steps=steps,
            latency_ms=latency_ms,
            screenshot_paths=screenshots,
        )

    async def _retry_click(self, page, test_id: str, retries: int = 2) -> None:
        last_error = None
        for _ in range(retries + 1):
            try:
                await page.get_by_test_id(test_id).click(timeout=5000)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                await asyncio.sleep(0.75)
        raise last_error

    async def _capture(self, page, path: Path, screenshots: list[str]) -> None:
        return None

    async def _pace(self) -> None:
        await asyncio.sleep(self.step_delay_s)

    def _notify(
        self,
        status: str,
        steps: list[dict],
        screenshots: list[str],
        failure_category: str | None,
        latency_ms: int | None,
    ) -> None:
        if self.progress_hook:
            self.progress_hook(
                status=status,
                steps=list(steps),
                screenshot_paths=list(screenshots),
                failure_category=failure_category,
                latency_ms=latency_ms,
            )

    async def _run_flow(self, page, browser, request, steps, screenshots, started) -> str | None:
        await page.goto(self.base_url, wait_until="networkidle")
        await page.wait_for_selector('[data-testid="search-input"]', timeout=10000)
        await page.wait_for_selector('[data-testid="session-ready"]', timeout=10000)
        steps.append({"action": "open_site", "status": "ok"})
        self._notify("running", steps, screenshots, None, None)
        await self._pace()

        if request.category:
            await page.get_by_test_id("category-filter").select_option(request.category)
        if request.filters.get("max_price"):
            await page.get_by_test_id("budget-input").fill(str(int(request.filters["max_price"])))

        await page.get_by_test_id("search-input").fill(request.query)
        await page.get_by_test_id("search-button").click()
        if request.product_id:
            await page.wait_for_selector(
                f'[data-testid="product-card"][data-product-id="{request.product_id}"]',
                timeout=10000,
            )
        else:
            await page.wait_for_selector('[data-testid="product-card"]', timeout=10000)
        steps.append({"action": "search", "query": request.query, "status": "ok"})
        self._notify("running", steps, screenshots, None, None)
        await self._pace()

        if request.product_id:
            card = page.locator(f'[data-testid="product-card"][data-product-id="{request.product_id}"]')
        else:
            card = page.locator('[data-testid="product-card"]').first
        await card.scroll_into_view_if_needed()
        await card.click()
        await page.wait_for_selector('[data-testid="add-to-cart-button"]', timeout=10000)
        steps.append({"action": "open_product", "status": "ok"})
        self._notify("running", steps, screenshots, None, None)
        await self._pace()

        await self._retry_click(page, "add-to-cart-button")
        await page.wait_for_function(
            """
            () => {
              const panel = document.querySelector('[data-testid="cart-panel"]');
              return panel && panel.innerText.toLowerCase().includes('items');
            }
            """,
            timeout=10000,
        )
        steps.append({"action": "add_to_cart", "status": "ok"})
        self._notify("running", steps, screenshots, None, None)
        await self._pace()

        await self._retry_click(page, "go-to-checkout-button")
        await page.wait_for_selector('[data-testid="approval-modal"]', timeout=10000)
        steps.append({"action": "await_approval", "status": "paused"})
        self._notify("running", steps, screenshots, None, None)
        await self._pace()

        if not request.checkout_approved:
            await browser.close()
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._notify("paused", steps, screenshots, None, latency_ms)
            return "paused"

        await self._retry_click(page, "approve-checkout-button")
        await page.wait_for_selector('[data-testid="checkout-success"]', timeout=10000)
        steps.append({"action": "checkout", "status": "confirmed"})
        self._notify("success", steps, screenshots, None, int((time.perf_counter() - started) * 1000))
