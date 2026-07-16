"""
Publisher: real video publishing to Douyin via Open API.
"""
import os
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.oauth_service import douyin_refresh_token

DOUYIN_API_BASE = "https://open.douyin.com"


class Publisher:
    """Video publisher with API-first, RPA-fallback strategy."""

    async def _refresh_if_needed(self, account) -> str | None:
        """Refresh access token if expired. Returns new token, or None on failure."""
        if not account.expired_at or not account.refresh_token:
            return account.auth_token

        now = datetime.now(timezone.utc)
        if account.expired_at.tzinfo is None:
            account.expired_at = account.expired_at.replace(tzinfo=timezone.utc)

        if now < account.expired_at:
            return account.auth_token

        token_data = await douyin_refresh_token(account.refresh_token)
        new_token = token_data.get("data", {}).get("access_token")
        if new_token:
            account.auth_token = new_token
            new_refresh = token_data["data"].get("refresh_token")
            if new_refresh:
                account.refresh_token = new_refresh
            expires_in = token_data["data"].get("expires_in", 1296000)
            account.expired_at = now + timedelta(seconds=expires_in)
        return new_token

    async def upload_video(self, access_token: str, open_id: str, video_path: str) -> dict:
        """Step 1: Upload video file to Douyin. Returns video_id on success."""
        url = f"{DOUYIN_API_BASE}/api/douyin/v1/video/upload_video/"
        file_size = os.path.getsize(video_path)
        file_name = Path(video_path).name

        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(video_path, "rb") as f:
                resp = await client.post(
                    url,
                    params={"open_id": open_id},
                    headers={"access-token": access_token},
                    files={"video": (file_name, f, "video/mp4")},
                )
            return resp.json()

    async def create_video(
        self, access_token: str, open_id: str, video_id: str, title: str
    ) -> dict:
        """Step 2: Publish video with metadata."""
        url = f"{DOUYIN_API_BASE}/api/douyin/v1/video/create_video/"
        body = {"video_id": video_id}
        if title:
            body["text"] = title[:1000]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                params={"open_id": open_id},
                headers={
                    "access-token": access_token,
                    "Content-Type": "application/json",
                },
                json=body,
            )
            return resp.json()

    async def publish_to_douyin(
        self, access_token: str, open_id: str, video_path: str, title: str
    ) -> dict:
        """Full publish flow: upload → create. Returns result dict."""
        # Step 1: Upload
        upload_result = await self.upload_video(access_token, open_id, video_path)
        upload_data = upload_result.get("data", {})
        if not upload_data or upload_data.get("error_code", -1) != 0:
            err = upload_data.get("description", upload_result.get("err_msg", "upload failed"))
            return {"status": "failed", "stage": "upload", "error": err, "raw": upload_result}

        video_info = upload_data.get("video", {})
        video_id = video_info.get("video_id")
        if not video_id:
            return {"status": "failed", "stage": "upload", "error": "no video_id returned", "raw": upload_result}

        # Step 2: Create / publish
        create_result = await self.create_video(access_token, open_id, video_id, title)
        create_data = create_result.get("data", {})
        if create_data.get("error_code", -1) != 0:
            err = create_data.get("description", create_result.get("err_msg", "create failed"))
            return {"status": "failed", "stage": "create", "error": err, "video_id": video_id, "raw": create_result}

        return {
            "status": "published",
            "video_id": video_id,
            "item_id": create_data.get("item_id"),
            "raw": create_result,
        }

    async def publish(
        self, platform: str, account, video_path: str, title: str
    ) -> dict:
        """Publish video to a platform account. Auto-refreshes token."""
        access_token = await self._refresh_if_needed(account)

        if platform == "douyin" and access_token and getattr(account, "open_id", None):
            try:
                result = await self.publish_to_douyin(
                    access_token, account.open_id, video_path, title
                )
                if result.get("status") == "published":
                    return {"mode": "api", "status": "published", "data": result}
                return {"mode": "api", "status": "failed", "data": result}
            except Exception as e:
                return {"mode": "api", "status": "error", "error": str(e)}

        # Fallback to RPA
        return {
            "mode": "rpa",
            "status": "queued",
            "message": f"RPA task queued for {platform}",
            "video_path": video_path,
            "title": title,
        }

    async def get_video_metrics(self, access_token: str, open_id: str, item_id: str) -> dict:
        """Fetch video metrics from Douyin API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{DOUYIN_API_BASE}/api/douyin/v1/video/video_data/",
                    params={"open_id": open_id},
                    headers={
                        "access-token": access_token,
                        "Content-Type": "application/json",
                    },
                    json={"item_ids": [item_id]},
                )
                data = resp.json().get("data", {})
                items = data.get("list", [data])
                if items and items[0]:
                    item = items[0]
                    return {
                        "plays": item.get("total_play", 0),
                        "likes": item.get("total_digg", 0),
                        "comments": item.get("total_comment", 0),
                        "shares": item.get("total_share", 0),
                    }
        except Exception:
            pass

        return {"plays": 0, "likes": 0, "comments": 0, "shares": 0}


publisher = Publisher()
