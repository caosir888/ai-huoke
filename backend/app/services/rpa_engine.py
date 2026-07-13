"""
RPA Engine: Playwright-based browser automation for platform operations.
Used as fallback when official APIs are unavailable or restricted.
"""
import asyncio
from typing import Optional


class RPAEngine:
    """
    Playwright-based RPA engine for platform automation.
    Manages browser sessions and executes platform-specific actions.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._sessions: dict[str, dict] = {}
        self._playwright = None
        self._browser = None

    async def start(self):
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except ImportError:
            pass  # Playwright not installed, RPA unavailable

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def get_session(self, account_id: str, platform: str) -> Optional[dict]:
        """Get or create a browser context for an account."""
        if not self._browser:
            return None

        session_key = f"{platform}:{account_id}"
        if session_key not in self._sessions:
            self._sessions[session_key] = await self._browser.new_context(
                storage_state=f"states/{session_key}.json",
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
        return self._sessions[session_key]

    async def publish_video_douyin(
        self, account_id: str, video_path: str, title: str
    ) -> dict:
        """Publish a video to Douyin via RPA."""
        session = await self.get_session(account_id, "douyin")
        if not session:
            return {"status": "failed", "error": "RPA engine not available"}

        try:
            page = await session.new_page()
            await page.goto("https://creator.douyin.com", wait_until="networkidle")
            await asyncio.sleep(2)

            # Click publish button
            await page.click('[data-e2e="publish-video"]')
            await page.wait_for_selector('input[type="file"]')
            await page.set_input_files('input[type="file"]', video_path)
            await page.wait_for_selector(".upload-success", timeout=120000)

            # Fill title
            await page.fill('[data-e2e="title-input"]', title)
            await asyncio.sleep(1)

            # Click submit
            await page.click('[data-e2e="submit-btn"]')
            await page.wait_for_selector(".publish-success", timeout=60000)

            await page.close()
            return {"status": "published", "mode": "rpa"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}


# Global RPA engine instance
rpa_engine = RPAEngine()
