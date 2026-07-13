import httpx
from app.config import settings


async def generate_copywriting(keywords: str, style: str, count: int = 5) -> list[dict]:
    """Generate short-video copywriting using DeepSeek API."""
    style_prompts = {
        "口播": "口播类短视频，有真人讲解感，语言流畅自然",
        "展示": "产品展示类视频，突出产品卖点和视觉冲击",
        "促销": "促销活动类视频，强调限时优惠和紧迫感",
        "剧情": "剧情类短视频，有故事性和反转效果",
    }

    prompt = f"""你是一个专业的短视频文案策划师，请为以下内容生成{count}条{style_prompts.get(style, '')}文案。

行业关键词：{keywords}

每条文案包含：
1. 标题（抓眼球，含数字或悬念）
2. 正文（适合{style}类视频的脚本文字，50-200字）
3. 话题标签（3-5个相关热门标签）

请严格按照以下JSON格式输出：
[{{"title": "...", "body": "...", "tags": "#tag1 #tag2"}}]

要求：
- 文案要有爆款潜质，前3秒能抓住用户注意力
- 语言口语化，贴近目标用户
- 每条文案风格略有不同，避免重复"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 3000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Extract JSON from response
        import json, re
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []


async def parse_video_link(url: str) -> dict | None:
    """Parse a viral video link and extract its copywriting structure."""
    prompt = f"""分析以下短视频链接的内容，提炼出它的文案结构和爆款逻辑：

链接：{url}

请分析并输出：
1. 标题公式（用了什么手法吸引点击）
2. 正文结构（开头-中间-结尾分别做了什么）
3. 话题标签策略
4. 可以模仿的关键要素

输出为JSON格式：
{{"title_formula": "...", "body_structure": "...", "tag_strategy": "...", "key_elements": "..."}}"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 1500,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        import json, re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
