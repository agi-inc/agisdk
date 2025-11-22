"""
Browser automation utilities built on patchright.

Provides a minimal AgentBrowser for managing browser instances with automatic popup handling
to support the simplified harness.
"""

from typing import Optional
import base64
from pathlib import Path
from patchright.async_api import Browser, BrowserContext, Page, async_playwright

from arena.image import Base64Image


class AgentBrowser:
    """
    Async context manager wrapper around Playwright browser for agent automation.

    Manages browser lifecycle and automatically handles popups by always returning
    the most recent page from the context.

    Example:
        async with AgentBrowser() as browser:
            await browser.page.goto("https://example.com")
            screenshot = await browser.screenshot()
    """

    def __init__(
        self,
        headless: bool = True,
        width: int = 1280,
        height: int = 720,
        wait_until: Optional[str] = "load",
        timeout: int = 30000,
    ):
        self.headless = headless
        self.width = width
        self.height = height
        self.wait_until = wait_until
        self.timeout = timeout
        self.locale = "en-US"
        self.timezone = "America/Los_Angeles"
        self.latitude = 34.0522
        self.longitude = -118.2437
        self.accept_language = "en-US,en;q=0.9"

        self._playwright = None
        self._browser = None
        self._context = None

    async def _inject_dropdown_handling(self):
        """This causes native selects (unseen by playwright) to be handled by the browser"""
        path_to_js: str = str(Path(__file__).parent / "proxy-select.js")
        path_to_css: str = str(Path(__file__).parent / "proxy-select.css")
        # Read and add JavaScript init script
        async def apply_proxy_scripts(page: Page):
            try:
                await page.add_init_script(js_script)
                await page.evaluate(js_script)
                await page.add_init_script(css_script)
                await page.evaluate(css_script)
            except Exception:
                pass

        with open(path_to_js, "r") as fd:
            js_script = fd.read()
            await self._context.add_init_script(js_script)

        # Read and add CSS init script
        with open(path_to_css, "r") as fd:
            css_content = fd.read()
            css_script = f"""
                (function() {{
                    function injectCSS() {{
                        if (document.querySelector('[data-proxy-select-css]')) {{
                            return;
                        }}
                        var style = document.createElement('style');
                        style.type = 'text/css';
                        style.setAttribute('data-proxy-select-css', 'true');
                        style.innerHTML = `{css_content}`;
                        document.head.appendChild(style);
                    }}

                    if (document.head) {{
                        injectCSS();
                    }} else {{
                        if (document.readyState === 'loading') {{
                            document.addEventListener('DOMContentLoaded', injectCSS);
                        }} else {{
                            injectCSS();
                        }}
                    }}
                }})();
            """
            await self._context.add_init_script(css_script)

        # Inject into current pages immediately
        for page in list(self._context.pages):
            await apply_proxy_scripts(page)

        # Ensure future pages also receive the scripts
        def _on_new_page(page: Page):
            try:
                import asyncio

                asyncio.create_task(apply_proxy_scripts(page))
            except Exception:
                pass

        try:
            self._context.on("page", _on_new_page)
        except Exception:
            pass

    async def __aenter__(self) -> "AgentBrowser":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()

        base_context_kwargs = {
            "viewport": {"width": self.width, "height": self.height},
            "locale": self.locale,
            "timezone_id": self.timezone,
            "geolocation": {"latitude": self.latitude, "longitude": self.longitude},
            "permissions": ["geolocation"],
            "extra_http_headers": {"Accept-Language": self.accept_language},
        }

        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(**base_context_kwargs)

        if self.timeout:
            self._context.set_default_timeout(self.timeout)

        await self._inject_dropdown_handling()

        if not self._context.pages:
            await self._context.new_page()

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def browser(self) -> Browser:
        return self._browser

    @property
    def context(self) -> BrowserContext:
        return self._context

    @property
    def page(self) -> Page:
        return self._context.pages[-1]

    async def screenshot(self, quality: int = 60) -> Base64Image:
        """Take a screenshot and return as Base64Image"""
        screenshot_bytes = await self.page.screenshot(type="jpeg", quality=quality)
        base64_string = base64.b64encode(screenshot_bytes).decode("utf-8")
        return Base64Image(base64_string)
