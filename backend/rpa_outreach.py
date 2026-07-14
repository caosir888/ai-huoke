"""
RPA Outreach Engine — Playwright-based DM sending for Douyin/Kuaishou/etc.

Two modes:
  - debug (default): Simulates sending, always succeeds. Set RPA_MODE=debug or leave unset.
  - real: Uses Playwright with a persistent browser profile. Requires RPA_MODE=real.

Environment variables for real mode:
  RPA_MODE=real
  RPA_PLATFORM=douyin
  RPA_PROFILE_DIR=./browser_profiles/douyin   # persistent browser profile
  RPA_HEADLESS=true                             # set to "false" to show browser
  RPA_DAILY_LIMIT=30                            # max DMs per account per day
  RPA_MIN_INTERVAL=180                          # min seconds between DMs
  RPA_MAX_INTERVAL=300                          # max seconds between DMs
"""

import os
import sys
import time
import random
import uuid
import asyncio
from pathlib import Path

RPA_MODE = os.environ.get("RPA_MODE", "debug")
RPA_PLATFORM = os.environ.get("RPA_PLATFORM", "douyin")
RPA_HEADLESS = os.environ.get("RPA_HEADLESS", "true").lower() != "false"
RPA_DAILY_LIMIT = int(os.environ.get("RPA_DAILY_LIMIT", "30"))
RPA_MIN_INTERVAL = int(os.environ.get("RPA_MIN_INTERVAL", "180"))
RPA_MAX_INTERVAL = int(os.environ.get("RPA_MAX_INTERVAL", "300"))

# Anti-detection: track per-session send count
_send_count: int = 0
_last_send_time: float = 0


def _random_delay():
    """Random delay between DMs to simulate human behavior."""
    delay = random.uniform(RPA_MIN_INTERVAL, RPA_MAX_INTERVAL)
    time.sleep(delay)


async def _random_delay_async():
    delay = random.uniform(RPA_MIN_INTERVAL, RPA_MAX_INTERVAL)
    await asyncio.sleep(delay)


# ============ Debug / Mock Mode ============

async def _execute_debug(tasks: list[dict]) -> list[dict]:
    """Simulate DM sending in debug mode. Always succeeds with a short delay."""
    results = []
    for i, task in enumerate(tasks):
        await asyncio.sleep(random.uniform(0.3, 1.2))  # simulate work
        results.append({
            "task_id": task["task_id"],
            "lead_id": task.get("lead_id", ""),
            "status": "sent",
            "message": f"[DEBUG] Mock DM sent to {task.get('lead_name', 'unknown')}: {task.get('content', '')[:50]}...",
        })
    return results


# ============ Real Mode (Playwright) ============

async def _execute_real(tasks: list[dict]) -> list[dict]:
    """Send real DMs using Playwright browser automation."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return [{"task_id": t["task_id"], "status": "failed",
                  "message": "Playwright not installed. Run: pip install playwright && playwright install chromium"} for t in tasks]

    global _send_count
    results = []

    profile_dir = Path(os.environ.get("RPA_PROFILE_DIR", "./browser_profiles/douyin"))
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=RPA_HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 390, "height": 844},  # mobile viewport
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                       "Version/16.0 Mobile/15E148 Safari/604.1",
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Check if logged in
        await page.goto("https://www.douyin.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        logged_in = await page.locator('text=登录').count() == 0
        if not logged_in:
            return [{"task_id": t["task_id"], "status": "failed",
                     "message": "未登录抖音，请先在浏览器中手动登录一次"} for t in tasks]

        for task in tasks:
            if _send_count >= RPA_DAILY_LIMIT:
                results.append({"task_id": task["task_id"], "status": "failed",
                                "message": f"已达每日上限 {RPA_DAILY_LIMIT} 条"})
                continue

            try:
                success, msg = await _send_one_dm(page, task)
                if success:
                    _send_count += 1
                    results.append({"task_id": task["task_id"], "status": "sent", "message": msg})
                else:
                    results.append({"task_id": task["task_id"], "status": "failed", "message": msg})

                await _random_delay_async()

            except Exception as e:
                results.append({"task_id": task["task_id"], "status": "failed", "message": str(e)[:200]})

        await browser.close()

    return results


async def _send_one_dm(page, task: dict) -> tuple[bool, str]:
    """Send one DM: navigate to user profile → click message button → send content + image."""
    lead_name = task.get("lead_name", "")
    content = task.get("content", "")
    image_url = task.get("image_url", "")

    # Navigate to search and find user
    await page.goto(f"https://www.douyin.com/search/{lead_name}?type=user", wait_until="domcontentloaded")
    await asyncio.sleep(random.uniform(2, 4))

    # Click first user result
    user_link = page.locator('[data-e2e="user-card"] a').first
    if await user_link.count() == 0:
        return False, f"未找到用户: {lead_name}"

    await user_link.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(random.uniform(2, 3))

    # Click "私信" button
    dm_btn = page.locator('button:has-text("私信"), span:has-text("私信"), div:has-text("私信")').first
    if await dm_btn.count() == 0:
        return False, f"找不到私信按钮，可能对方限制了私信权限"

    await dm_btn.click()
    await asyncio.sleep(random.uniform(1, 2))

    # Type message
    text_area = page.locator('textarea, [contenteditable="true"], div[data-e2e="chat-input"]').first
    if await text_area.count() > 0:
        await text_area.fill(content)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # If there's an image, upload it
    if image_url:
        try:
            file_input = page.locator('input[type="file"]').first
            if await file_input.count() > 0:
                # Download image first
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(image_url)
                    if resp.status_code == 200:
                        tmp = Path(f"/tmp/rpa_img_{uuid.uuid4().hex[:6]}.jpg")
                        tmp.write_bytes(resp.content)
                        await file_input.set_input_files(str(tmp))
                        await asyncio.sleep(1)
                        tmp.unlink(missing_ok=True)
        except Exception:
            pass  # Image upload failed, still send text

    # Click send button
    send_btn = page.locator('button:has-text("发送"), [data-e2e="send-btn"], span:has-text("发送")').first
    if await send_btn.count() == 0:
        # Try pressing Enter instead
        await page.keyboard.press("Enter")
    else:
        await send_btn.click()

    await asyncio.sleep(random.uniform(1, 2))
    return True, f"已发送私信给 {lead_name}"


# ============ Public API ============

async def execute_batch(tasks: list[dict]) -> list[dict]:
    """Execute a batch of outreach tasks. Dispatches to debug or real mode."""
    if not tasks:
        return []

    if RPA_MODE == "real":
        return await _execute_real(tasks)
    else:
        return await _execute_debug(tasks)


def execute_batch_sync(tasks: list[dict]) -> list[dict]:
    """Synchronous wrapper for calling from non-async context."""
    return asyncio.run(execute_batch(tasks))
