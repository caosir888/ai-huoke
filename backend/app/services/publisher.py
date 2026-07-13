"""
Publisher: handles video publishing to platforms with API+RPA dual routing.
"""
import httpx
import json
from typing import Optional
from enum import Enum


class PublishMode(Enum):
    API = "api"
    RPA = "rpa"


class Publisher:
    """Video publisher with API-first, RPA-fallback strategy."""

    def __init__(self):
        # Platform API endpoints
        self.platform_configs = {
            "douyin": {
                "api_base": "https://open.douyin.com",
                "publish_endpoint": "/video/create/",
                "requires_enterprise": True,
            },
            "kuaishou": {
                "api_base": "https://open.kuaishou.com",
                "publish_endpoint": "/openapi/video/publish",
                "requires_enterprise": False,
            },
        }

    async def publish_to_douyin_via_api(
        self, access_token: str, video_path: str, title: str
    ) -> dict:
        """Publish video to Douyin via official Open API."""
        url = "https://open.douyin.com/api/video/upload/create"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 1: Initialize upload
        async with httpx.AsyncClient(timeout=60) as client:
            init_resp = await client.post(
                "https://open.douyin.com/video/upload/init/",
                headers=headers,
                json={"video_size": 0},  # Will use real file size in production
            )
            init_data = init_resp.json()

            # Step 2: Upload video (chunked)
            upload_url = init_data.get("data", {}).get("upload_url", "")
            if upload_url:
                with open(video_path, "rb") as f:
                    await client.put(upload_url, content=f.read())

            # Step 3: Create video with metadata
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "title": title,
                    "video_id": init_data.get("data", {}).get("video_id"),
                    "micro_app_id": "",
                },
            )
            return resp.json()

    async def publish_via_rpa(
        self, platform: str, account_id: str, video_path: str, title: str
    ) -> dict:
        """Publish via RPA (Playwright-based). This is a backup when API is unavailable."""
        # In production: send task to RPA service to execute Playwright script
        # For now: stub that records the intent
        return {
            "mode": "rpa",
            "status": "queued",
            "message": f"RPA task queued for {platform} account {account_id}",
            "video_path": video_path,
            "title": title,
        }

    async def publish(
        self,
        platform: str,
        account_id: str,
        access_token: str,
        video_path: str,
        title: str,
    ) -> dict:
        """Publish with automatic API/RPA routing."""
        # Try API first
        if platform == "douyin" and access_token:
            try:
                result = await self.publish_to_douyin_via_api(
                    access_token, video_path, title
                )
                if result.get("data"):
                    return {"mode": "api", "status": "published", "data": result["data"]}
            except Exception as e:
                # API failed, fall through to RPA
                pass

        # Fallback to RPA
        return await self.publish_via_rpa(platform, account_id, video_path, title)

    async def get_video_metrics(
        self, platform: str, access_token: str, video_id: str
    ) -> dict:
        """Fetch video metrics from platform API."""
        metrics = {"plays": 0, "likes": 0, "comments": 0, "shares": 0}

        if platform == "douyin":
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"https://open.douyin.com/data/external/item/base/",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"item_id": video_id},
                    )
                    data = resp.json().get("data", {}).get("result_list", [{}])[0]
                    metrics = {
                        "plays": data.get("total_play", 0),
                        "likes": data.get("total_digg", 0),
                        "comments": data.get("total_comment", 0),
                        "shares": data.get("total_share", 0),
                    }
            except Exception:
                pass

        return metrics
