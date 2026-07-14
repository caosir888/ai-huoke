"""
本地开发服务器 — 使用 SQLite，无需安装任何数据库。
启动: python server.py
"""
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import uuid
import json
import asyncio
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta, timezone

# China Standard Time (UTC+8)
CST = timezone(timedelta(hours=8))

def now_cst() -> datetime:
    """Return current datetime in China Standard Time."""
    return datetime.now(CST)

import httpx

# Patch config to use SQLite before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./aihuoke.db"

# DeepSeek API config
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = "deepseek-chat"

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

app = FastAPI(title="AI获客", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Videos output directory
VIDEOS_DIR = Path("videos")
VIDEOS_DIR.mkdir(exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

# SQLite async engine
DATABASE_URL = "sqlite+aiosqlite:///./aihuoke.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

security = HTTPBearer()

# ============ In-memory stores ============
codes: dict[str, str] = {}
users: dict[str, dict] = {}

# ============ DB Helpers ============

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

def get_token_user(auth: HTTPAuthorizationCredentials = Depends(security)) -> dict | None:
    token = auth.credentials
    user = users.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user

# ============ Auth ============

class SendCodeReq(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")

class LoginReq(BaseModel):
    phone: str
    code: str

class UpdateProfileReq(BaseModel):
    industry: str | None = None
    company_name: str | None = None

@app.post("/auth/send-code")
async def send_code(req: SendCodeReq):
    codes[req.phone] = "8888"
    return {"message": "验证码已发送", "debug_code": "8888"}

@app.post("/auth/login")
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    if codes.get(req.phone) != req.code:
        raise HTTPException(status_code=400, detail="验证码错误")

    # Check existing user in SQLite
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, phone, industry, company_name, plan_type FROM users WHERE phone = :phone"), {"phone": req.phone})
    row = result.fetchone()

    if row:
        uid = row[0]
        user_data = {"id": uid, "phone": row[1], "industry": row[2], "company_name": row[3], "plan_type": row[4]}
    else:
        uid = str(uuid.uuid4())
        user_data = {"id": uid, "phone": req.phone, "industry": None, "company_name": None, "plan_type": "free"}
        await db.execute(text(
            "INSERT INTO users (id, phone, password_hash, industry, company_name, plan_type, is_active, created_at, updated_at) "
            "VALUES (:id, :phone, '', :industry, :company, 'free', 1, :now, :now)"
        ), {"id": uid, "phone": req.phone, "industry": None, "company": None, "now": now_cst().isoformat()})
        # Init quota
        await db.execute(text(
            "INSERT INTO user_quotas (id, user_id, daily_video_count, monthly_video_count, account_limit, storage_bytes_used, storage_bytes_limit, updated_at) "
            "VALUES (:id, :uid, 3, 30, 1, 0, 1073741824, :now)"
        ), {"id": str(uuid.uuid4()), "uid": uid, "now": now_cst().isoformat()})
        await db.commit()

    token = f"tok_{uid[:8]}_{uuid.uuid4().hex[:8]}"
    users[token] = user_data
    del codes[req.phone]
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me")
async def get_me(user: dict = Depends(get_token_user)):
    return user

@app.put("/auth/profile")
async def update_profile(req: UpdateProfileReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    if req.industry is not None:
        user["industry"] = req.industry
        await db.execute(text("UPDATE users SET industry = :ind WHERE id = :uid"), {"ind": req.industry, "uid": user["id"]})
    if req.company_name is not None:
        user["company_name"] = req.company_name
        await db.execute(text("UPDATE users SET company_name = :cn WHERE id = :uid"), {"cn": req.company_name, "uid": user["id"]})
    await db.commit()
    return user

# ============ Content ============

class GenerateCopywritingReq(BaseModel):
    keywords: str
    style: str = "口播"
    count: int = 5
    industry: str = "通用"
    reference_structure: dict | None = None

class ParseLinkReq(BaseModel):
    url: str

# ============ DeepSeek AI helpers ============

COPYWRITING_SYSTEM_PROMPT = """你是一个短视频营销文案专家，专注于为中国商家撰写抖音/快手/小红书平台的爆款短视频文案。

你的每条文案必须包含以下结构：
1. 标题：10-20字，抓眼球，用数字/疑问/夸张手法
2. 正文：150-300字，包含开场钩子(前3秒)→产品卖点→使用场景→优惠/行动号召
3. 标签：3-5个#话题标签

根据风格调整：
- 口播型：口语化，像跟朋友聊天，多用感叹词
- 展示型：视觉化描述+产品特写+使用效果，多用画面引导词
- 教程型：步骤化讲解，数字编号，简单易懂
- 促销型：强调优惠力度、限时限量、紧迫感
- 剧情型：有开头冲突+反转+产品植入

输出格式为JSON数组，每个元素包含 title, body, tags 三个字段。不要输出其他内容。"""

async def call_deepseek(user_prompt: str, system_prompt: str = COPYWRITING_SYSTEM_PROMPT) -> list[dict] | None:
    """调用DeepSeek API生成文案。失败返回None。"""
    if not DEEPSEEK_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 4096,
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Parse JSON from response (strip markdown code fences if present)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            return json.loads(content)
    except Exception:
        return None

STYLE_TEMPLATES = {
    "口播": {
        "openings": [
            "兄弟们，今天给你们安利一个{keyword}，真的太绝了！",
            "你敢信？这个{keyword}居然这么好吃/好用！",
            "作为一个{industry}老司机，我强烈推荐{keyword}！",
        ],
        "body_template": "{opening}\n\n{points}\n\n{closing}",
        "closings": [
            "还在犹豫什么？点击下方链接，赶紧试试吧！",
            "我身边的朋友都入手了，你还在等什么？",
            "优惠名额有限，先到先得！",
        ],
    },
    "教程": {
        "openings": [
            "30秒教会你{keyword}，小白也能学会！",
            "今天分享一个{keyword}的神仙做法，学会了直接开店！",
            "别再花冤枉钱了！{keyword}正确打开方式来啦~",
        ],
        "closings": [
            "学会了吗？记得点赞收藏，关注我学更多干货！",
            "还想学什么？评论区告诉我，下期安排！",
        ],
    },
    "展示": {
        "openings": [
            "看这个{keyword}，这品质真的绝了！",
            "{keyword}到底有多好？给你们近距离看看！",
        ],
        "closings": [
            "想了解更多细节，私信我发你完整介绍~",
        ],
    },
    "促销": {
        "openings": [
            "重磅福利！{keyword}现在只要XX元，错过等一年！",
            "年底清仓！{keyword}打骨折，手慢无！",
        ],
        "closings": [
            "库存不多，今天不买明天就恢复原价！点击下单！",
        ],
    },
    "剧情": {
        "openings": [
            "老板说这个{keyword}卖不出去就要辞退我...",
            "闺蜜说我做的{keyword}是黑暗料理？结果她吃了三碗...",
        ],
        "closings": [
            "后续更精彩，关注我追更！",
        ],
    },
}

INDUSTRY_TAGS = {
    "餐饮": ["美食探店", "美食推荐", "吃货", "必吃榜", "团购"],
    "美业": ["皮肤管理", "美容护肤", "变美", "好物分享", "体验"],
    "汽车": ["汽车", "买车", "汽车用品", "好车推荐"],
    "零售": ["好物推荐", "开箱", "性价比", "必买清单"],
    "家居": ["家居好物", "装修", "生活美学", "居家好物"],
    "教育": ["学习", "知识分享", "干货", "考证", "技能"],
    "医疗": ["健康科普", "养生", "健康", "体检"],
}

def generate_fallback(keywords: str, style: str, count: int, industry: str = "通用") -> list[dict]:
    """无API key时使用模板生成可用文案（非占位符）。"""
    import random
    style_cfg = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["口播"])
    tags_pool = INDUSTRY_TAGS.get(industry, ["好物推荐", "必买清单", "干货分享", "教程"])
    results = []
    for i in range(count):
        opening = random.choice(style_cfg["openings"]).format(keyword=keywords, industry=industry)
        closing = random.choice(style_cfg["closings"]).format(keyword=keywords, industry=industry)

        # Build body based on industry
        if industry == "餐饮":
            points = (
                f"第一，{keywords}的食材选用上等原料，绝不偷工减料。\n"
                f"第二，制作工艺传承古法，每一道工序都严格把控。\n"
                f"第三，价格实惠，性价比超高，人均消费不到50块。"
            )
            default_tags = ["美食探店", "美食推荐", "必吃榜"]
        elif industry == "美业":
            points = (
                f"第一，{keywords}采用进口设备，安全无痛。\n"
                f"第二，店长拥有10年经验，技术过硬。\n"
                f"第三，现在体验价仅需99元，还送一次免费补水面膜。"
            )
            default_tags = ["皮肤管理", "变美日记", "体验分享"]
        elif industry == "零售":
            points = (
                f"第一，{keywords}一手货源，品质有保障。\n"
                f"第二，支持一件代发，零库存零风险。\n"
                f"第三，7天无理由退换，售后无忧。"
            )
            default_tags = ["好物推荐", "一件代发", "源头好货"]
        else:
            points = (
                f"第一，{keywords}质量过硬，用过的都说好。\n"
                f"第二，价格实惠，同样品质只要一半的价格。\n"
                f"第三，服务到位，售后无忧，值得信赖。"
            )
            default_tags = tags_pool[:3]

        title = f"{keywords} — {random.choice(['真的绝了', '太划算了', '必入推荐', '实测分享', '种草推荐'])}"
        body = style_cfg["body_template"].format(
            opening=opening, points=points, closing=closing
        )
        tags = " ".join(f"#{t}" for t in random.sample(default_tags + tags_pool, min(5, len(default_tags) + len(tags_pool))))

        results.append({"title": title, "body": body, "tags": tags})

    return results

class CreateFolderReq(BaseModel):
    name: str
    parent_id: str | None = None

class CreateEditTaskReq(BaseModel):
    material_ids: list[str]
    copywriting_id: str | None = None
    template_id: str = "mix"
    count: int = 5
    duration: int = 30
    ratio: str = "9:16"
    voice: str = "female"
    subtitle_style: str = "white_black_border"

@app.get("/content/copywriting/list")
async def list_copywriting(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, title, body, tags, style, source, is_favorited, created_at FROM copywriting_templates WHERE user_id = :uid ORDER BY created_at DESC LIMIT 50"), {"uid": user["id"]})
    rows = result.fetchall()
    if not rows:
        # Return seed data for demo
        now = now_cst().isoformat()
        return [
            {"id": "demo1", "title": "重庆火锅 — 正宗牛油锅底", "body": "在重庆，没有一顿火锅解决不了的事！\n\n我们家的锅底，用了28味中草药和上等牛油，熬足8小时。看这翻滚的红汤，光闻着就流口水了吧？\n\n必点菜品：鲜毛肚，七上八下15秒，蘸上香油蒜泥，一口下去那个脆嫩……绝了！\n\n现在团购价只要128元，2-3人吃到撑。", "tags": "#重庆火锅 #火锅探店", "style": "口播", "source": "ai", "is_favorited": False, "created_at": now},
            {"id": "demo2", "title": "夏天必喝的爆款柠檬茶", "body": "30秒教会你做一杯好喝到爆的暴打柠檬茶！🍋\n\n新鲜香水柠檬切片，加冰暴打，把柠檬的香气打出来。倒入秘制茶底，一杯成本不到3块，卖15块！\n\n想了解更多饮品配方，关注我下期分享。", "tags": "#柠檬茶 #饮品教程", "style": "教程", "source": "ai", "is_favorited": True, "created_at": now},
            {"id": "demo3", "title": "99元体验韩国明星同款皮肤管理", "body": "姐妹们，这家藏在写字楼里的宝藏皮肤管理店！\n\n韩国进口仪器，院长10年经验。99元体验：深层清洁+玻尿酸导入+LED光疗+补水面膜。全程60分钟无推销。", "tags": "#皮肤管理 #美容院探店", "style": "展示", "source": "ai", "is_favorited": False, "created_at": now},
        ]
    return [{"id": r[0], "title": r[1], "body": r[2], "tags": r[3], "style": r[4], "source": r[5], "is_favorited": bool(r[6]), "created_at": r[7]} for r in rows]

@app.post("/content/copywriting/generate")
async def generate_copywriting(req: GenerateCopywritingReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    now = now_cst().isoformat()

    # Try DeepSeek API first
    prompt = f"请为以下产品/服务生成{req.count}条短视频营销文案：\n关键词：{req.keywords}\n行业：{req.industry}\n风格：{req.style}"

    if req.reference_structure:
        ref = req.reference_structure
        prompt += (
            f"\n请模仿以下爆款结构来创作："
            f"\n- 标题公式：{ref.get('title_formula', '')}"
            f"\n- 正文结构：{ref.get('body_structure', '')}"
            f"\n- 标签策略：{ref.get('tag_strategy', '')}"
            f"\n- 可模仿要素：{ref.get('key_elements', '')}"
        )
    items = await call_deepseek(prompt)

    if items is None:
        # DeepSeek unavailable, use template fallback
        items = generate_fallback(req.keywords, req.style, req.count, req.industry)

    generated = []
    for i, item in enumerate(items[: req.count]):
        cid = str(uuid.uuid4())
        title = item.get("title", f"{req.keywords}文案{i+1}")
        body = item.get("body", "")
        tags = item.get("tags", f"#{req.keywords}")
        # DeepSeek may return tags as a JSON array, normalize to string
        if isinstance(tags, list):
            tags = " ".join(f"#{t.strip('#')}" for t in tags)
        await db.execute(text(
            "INSERT INTO copywriting_templates (id, user_id, title, body, tags, style, source, is_favorited, created_at) VALUES (:id, :uid, :title, :body, :tags, :style, 'ai', 0, :now)"
        ), {"id": cid, "uid": user["id"], "title": title, "body": body, "tags": tags, "style": req.style, "now": now})
        generated.append({"id": cid, "title": title, "body": body, "tags": tags, "style": req.style, "source": "ai", "is_favorited": False, "created_at": now})

    await db.commit()
    return generated

@app.post("/content/copywriting/parse-link")
async def parse_link(req: ParseLinkReq, user: dict = Depends(get_token_user)):
    # Try DeepSeek
    prompt = f"请分析这个短视频链接的内容结构，拆解出：标题公式、正文结构、标签策略、关键元素。链接：{req.url}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个短视频内容分析专家。分析爆款视频的结构，拆解其公式。返回JSON格式：{\"title_formula\":\"...\", \"body_structure\":\"...\", \"tag_strategy\":\"...\", \"key_elements\":\"...\"}，不要输出其他内容。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 1024,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                    if content.endswith("```"):
                        content = content[:-3]
                return json.loads(content)
    except Exception:
        pass

    # Fallback
    return {
        "title_formula": "痛点+解决方案+优惠",
        "body_structure": "开场3秒抓眼球→展示产品→价格锚点→限时优惠→引导行动",
        "tag_strategy": "#行业词 #场景词 #热搜词",
        "key_elements": "1.夸张开场 2.价格对比 3.紧迫感 4.行动指令"
    }

@app.post("/content/materials/upload")
async def upload_material(file: UploadFile = File(...), folder_id: str | None = Form(None), user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text

    # Detect file type from extension
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"):
        ftype = "video"
    elif ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        ftype = "image"
    elif ext in (".mp3", ".wav", ".aac", ".ogg", ".m4a"):
        ftype = "audio"
    else:
        ftype = "other"

    # Create user upload subdirectory
    user_dir = UPLOAD_DIR / user["id"]
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save file to disk
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = user_dir / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    file_size = len(content)

    mid = str(uuid.uuid4())
    rel_url = f"/uploads/{user['id']}/{safe_name}"
    now = now_cst().isoformat()

    await db.execute(text(
        "INSERT INTO materials (id, user_id, folder_id, type, file_name, file_url, size, duration, tags, created_at) VALUES (:id, :uid, :fid, :type, :name, :url, :size, :dur, '{}', :now)"
    ), {"id": mid, "uid": user["id"], "fid": folder_id, "type": ftype, "name": file.filename, "url": rel_url, "size": file_size, "dur": None, "now": now})
    # Track storage usage
    await db.execute(text(
        "UPDATE user_quotas SET storage_bytes_used = storage_bytes_used + :size, updated_at = :now WHERE user_id = :uid"
    ), {"size": file_size, "uid": user["id"], "now": now})
    await db.commit()
    return {"id": mid, "type": ftype, "file_name": file.filename, "file_url": rel_url, "thumbnail_url": None, "duration": None, "size": file_size, "tags": [], "created_at": now}

@app.get("/content/materials")
async def list_materials(
    user: dict = Depends(get_token_user),
    db: AsyncSession = Depends(get_db),
    type: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    from sqlalchemy import text
    allowed_sort = {"created_at", "size", "file_name", "duration"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    conditions = ["user_id = :uid"]
    params: dict = {"uid": user["id"]}

    if type:
        conditions.append("type = :type")
        params["type"] = type
    if search:
        conditions.append("(file_name LIKE :kw OR tags LIKE :kw)")
        params["kw"] = f"%{search}%"

    where = " AND ".join(conditions)
    query = f"SELECT id, type, file_name, file_url, thumbnail_url, duration, size, tags, created_at FROM materials WHERE {where} ORDER BY {sort_by} {sort_order} LIMIT 200"
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [{"id": r[0], "type": r[1], "file_name": r[2], "file_url": r[3], "thumbnail_url": r[4], "duration": r[5], "size": r[6], "tags": r[7].split(",") if isinstance(r[7], str) else [], "created_at": r[8]} for r in rows]

@app.delete("/content/materials/{material_id}")
async def delete_material(material_id: str, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    # Get file_url and size before deleting the record
    result = await db.execute(text("SELECT file_url, size FROM materials WHERE id=:id AND user_id=:uid"), {"id": material_id, "uid": user["id"]})
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "素材不存在")
    file_path = UPLOAD_DIR / row[0].lstrip("/uploads/")
    file_size = row[1] or 0
    await db.execute(text("DELETE FROM materials WHERE id=:id AND user_id=:uid"), {"id": material_id, "uid": user["id"]})
    # Track storage usage
    now = now_cst().isoformat()
    await db.execute(text(
        "UPDATE user_quotas SET storage_bytes_used = MAX(0, storage_bytes_used - :size), updated_at = :now WHERE user_id = :uid"
    ), {"size": file_size, "uid": user["id"], "now": now})
    await db.commit()
    # Clean up file on disk
    if file_path.exists():
        file_path.unlink(missing_ok=True)
    return {"ok": True}


@app.post("/content/materials/batch-delete")
async def batch_delete_materials(req: dict, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    """Batch delete materials by IDs. Body: {ids: [...]}"""
    from sqlalchemy import text
    ids = req.get("ids", [])
    if not ids:
        raise HTTPException(400, "请提供要删除的素材ID列表")
    deleted = 0
    total_freed = 0
    for mid in ids:
        result = await db.execute(text("SELECT file_url, size FROM materials WHERE id=:id AND user_id=:uid"), {"id": mid, "uid": user["id"]})
        row = result.fetchone()
        if row:
            file_path = UPLOAD_DIR / row[0].lstrip("/uploads/")
            total_freed += row[1] or 0
            await db.execute(text("DELETE FROM materials WHERE id=:id AND user_id=:uid"), {"id": mid, "uid": user["id"]})
            if file_path.exists():
                file_path.unlink(missing_ok=True)
            deleted += 1
    if total_freed > 0:
        now = now_cst().isoformat()
        await db.execute(text(
            "UPDATE user_quotas SET storage_bytes_used = MAX(0, storage_bytes_used - :size), updated_at = :now WHERE user_id = :uid"
        ), {"size": total_freed, "uid": user["id"], "now": now})
    await db.commit()
    return {"ok": True, "deleted": deleted}


@app.get("/content/folders")
async def list_folders(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, name, parent_id, created_at FROM material_folders WHERE user_id = :uid ORDER BY created_at"), {"uid": user["id"]})
    rows = result.fetchall()
    return [{"id": r[0], "name": r[1], "parent_id": r[2], "created_at": r[3]} for r in rows]

@app.post("/content/folders")
async def create_folder(req: CreateFolderReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    fid = str(uuid.uuid4())
    now = now_cst().isoformat()
    await db.execute(text("INSERT INTO material_folders (id, user_id, name, parent_id, created_at) VALUES (:id, :uid, :name, :pid, :now)"), {"id": fid, "uid": user["id"], "name": req.name, "pid": req.parent_id, "now": now})
    await db.commit()
    return {"id": fid, "name": req.name, "parent_id": req.parent_id, "created_at": now}

@app.post("/content/edit-tasks")
async def create_edit_task(req: CreateEditTaskReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text

    # Quota check: count today's and this month's tasks
    today_start = now_cst().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    month_start = now_cst().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    daily_res = await db.execute(text(
        "SELECT COUNT(*) FROM edit_tasks WHERE user_id = :uid AND created_at >= :today"
    ), {"uid": user["id"], "today": today_start})
    daily_used = daily_res.fetchone()[0]
    monthly_res = await db.execute(text(
        "SELECT COUNT(*) FROM edit_tasks WHERE user_id = :uid AND created_at >= :month"
    ), {"uid": user["id"], "month": month_start})
    monthly_used = monthly_res.fetchone()[0]

    # Get user's quota limits
    q_res = await db.execute(text(
        "SELECT daily_video_count, monthly_video_count FROM user_quotas WHERE user_id = :uid"
    ), {"uid": user["id"]})
    q_row = q_res.fetchone()
    daily_limit = q_row[0] if q_row else 3
    monthly_limit = q_row[1] if q_row else 30

    if daily_used >= daily_limit:
        raise HTTPException(429, f"今日配额已用完（{daily_used}/{daily_limit}），请明天再试或升级套餐")
    if monthly_used >= monthly_limit:
        raise HTTPException(429, f"本月配额已用完（{monthly_used}/{monthly_limit}），请下月再试或升级套餐")

    tid = str(uuid.uuid4())
    now = now_cst().isoformat()
    await db.execute(text("INSERT INTO edit_tasks (id, user_id, material_ids, copywriting_id, template_id, params, status, progress, output_urls, created_at) VALUES (:id, :uid, :mids, :cid, :tid, :params, 'pending', 0, '', :now)"), {"id": tid, "uid": user["id"], "mids": ",".join(req.material_ids), "cid": req.copywriting_id, "tid": req.template_id, "params": req.model_dump_json(), "now": now})
    await db.commit()

    # Fire background simulation
    asyncio.create_task(_simulate_edit(tid, req.count, user["id"]))

    return {"id": tid, "material_ids": req.material_ids, "status": "pending", "progress": 0, "output_urls": [], "error_message": None, "created_at": now}

async def _simulate_edit(task_id: str, count: int, user_id: str):
    """Real FFmpeg video mixing using mixer.py."""
    import random
    from sqlalchemy import text as sql_text

    async with async_session() as db:
        try:
            # Fetch all material file paths
            result = await db.execute(sql_text("SELECT material_ids FROM edit_tasks WHERE id=:id"), {"id": task_id})
            row = result.fetchone()
            input_files = []
            if row and row[0]:
                mat_ids = row[0].split(",")
                for mid in mat_ids:
                    mat_result = await db.execute(sql_text("SELECT file_url FROM materials WHERE id=:id"), {"id": mid})
                    mat_row = mat_result.fetchone()
                    if mat_row:
                        src_path = UPLOAD_DIR / mat_row[0].lstrip("/uploads/")
                        if src_path.exists():
                            input_files.append(str(src_path))

            # Mark as processing
            await db.execute(sql_text("UPDATE edit_tasks SET status='processing', progress=10 WHERE id=:id"), {"id": task_id})
            await db.commit()

            # Fetch copywriting + voice + duration params
            copywriting_text = ""
            voice = "none"
            template_id = "mix"
            total_duration = 30  # default 30s
            ratio = "16:9"
            task_result = await db.execute(sql_text("SELECT copywriting_id, params FROM edit_tasks WHERE id=:id"), {"id": task_id})
            task_row = task_result.fetchone()
            if task_row:
                if task_row[0]:
                    cw_content = await db.execute(sql_text("SELECT body FROM copywriting_templates WHERE id=:id"), {"id": task_row[0]})
                    cw_content_row = cw_content.fetchone()
                    if cw_content_row and cw_content_row[0]:
                        copywriting_text = cw_content_row[0][:300]
                if task_row[1]:
                    try:
                        params = json.loads(task_row[1])
                        voice = params.get("voice", "none")
                        total_duration = params.get("duration", 30)
                        template_id = params.get("template_id", "mix")
                        ratio = params.get("ratio", "16:9")
                    except (json.JSONDecodeError, TypeError):
                        pass

            # === Real FFmpeg mixing (run in thread to not block event loop) ===
            out_dir = VIDEOS_DIR / user_id
            out_dir.mkdir(parents=True, exist_ok=True)

            import mixer
            output_paths = await asyncio.to_thread(
                mixer.mix_videos,
                input_files=input_files,
                output_dir=str(out_dir),
                count=count,
                total_duration=total_duration,
                subtitle=copywriting_text,
                voice=voice,
                template=template_id,
                ratio=ratio,
            )
            # =========================

            # Dedup quality check
            quality_report = {}
            if len(output_paths) > 1:
                quality_report = await asyncio.to_thread(
                    mixer.check_dedup_quality, output_paths
                )
                if not quality_report.get("passed", True):
                    print(f"[EDIT] WARNING: Dedup quality low - {quality_report.get('dedup_ratio', '?')} unique")
                else:
                    print(f"[EDIT] Dedup quality OK - {quality_report.get('dedup_ratio', '?')} unique ({quality_report.get('unique_count')}/{quality_report.get('total_count')})")

            # Build relative URLs from output paths + generate thumbnails
            output_urls = []
            thumbnail_urls = []
            for op in output_paths:
                fname = Path(op).name
                output_urls.append(f"/videos/{user_id}/{fname}")
                # Generate thumbnail from first frame
                thumb_path = await asyncio.to_thread(mixer.make_thumbnail, op)
                if thumb_path:
                    thumbnail_urls.append(f"/videos/{user_id}/{Path(thumb_path).name}")

            await db.execute(sql_text(
                "UPDATE edit_tasks SET status='done', progress=100, output_urls=:urls, quality_report=:qr, thumbnail_urls=:thumbs WHERE id=:id"
            ), {"urls": ",".join(output_urls), "qr": json.dumps(quality_report) if quality_report else "", "thumbs": ",".join(thumbnail_urls), "id": task_id})
            await db.commit()

        except Exception as e:
            await db.execute(sql_text(
                "UPDATE edit_tasks SET status='failed', error_message=:msg WHERE id=:id"
            ), {"msg": str(e), "id": task_id})
            await db.commit()

@app.get("/content/edit-tasks")
async def list_edit_tasks(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, material_ids, status, progress, output_urls, thumbnail_urls, error_message, quality_report, created_at FROM edit_tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 50"), {"uid": user["id"]})
    rows = result.fetchall()
    return [{"id": r[0], "material_ids": r[1].split(",") if isinstance(r[1], str) and r[1] else [], "status": r[2], "progress": r[3], "output_urls": r[4].split(",") if isinstance(r[4], str) and r[4] else [], "thumbnail_urls": r[5].split(",") if isinstance(r[5], str) and r[5] else [], "error_message": r[6], "quality_report": json.loads(r[7]) if r[7] else None, "created_at": r[8]} for r in rows]

# ============ Publish ============

class CreatePublishTaskReq(BaseModel):
    video_url: str
    platform_account_id: str
    title: str
    schedule_type: str = "now"
    schedule_time: str | None = None

@app.get("/publish/tasks")
async def list_publish_tasks(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, video_url, platform_account_id, title, schedule_type, schedule_time, status, progress, publish_result, metrics, error_message, created_at FROM publish_tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 100"), {"uid": user["id"]})
    rows = result.fetchall()
    import json
    return [{"id": r[0], "video_url": r[1], "platform_account_id": r[2], "title": r[3], "schedule_type": r[4], "schedule_time": r[5], "status": r[6], "progress": r[7], "publish_result": json.loads(r[8]) if r[8] else None, "metrics": json.loads(r[9]) if r[9] else {}, "error_message": r[10], "created_at": r[11]} for r in rows]

@app.post("/publish/tasks")
async def create_publish_task(req: CreatePublishTaskReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    import json
    tid = str(uuid.uuid4())
    now = now_cst().isoformat()
    # Start as "publishing" so UI shows progress
    initial_status = "publishing" if req.schedule_type == "now" else "pending"
    await db.execute(text(
        "INSERT INTO publish_tasks (id, user_id, video_url, platform_account_id, title, schedule_type, schedule_time, status, progress, metrics, created_at) "
        "VALUES (:id, :uid, :url, :aid, :title, :st, :sch, :status, :prog, :metrics, :now)"
    ), {"id": tid, "uid": user["id"], "url": req.video_url, "aid": req.platform_account_id, "title": req.title,
        "st": req.schedule_type, "sch": req.schedule_time, "status": initial_status, "prog": 0,
        "metrics": json.dumps({"plays": 0, "likes": 0, "comments": 0, "shares": 0}), "now": now})
    await db.commit()

    if req.schedule_type == "now":
        asyncio.create_task(_simulate_publish(tid, user["id"]))

    return {"id": tid, "video_url": req.video_url, "platform_account_id": req.platform_account_id,
            "title": req.title, "schedule_type": req.schedule_type, "schedule_time": req.schedule_time,
            "status": initial_status, "publish_result": None, "metrics": {}, "created_at": now}


async def _simulate_publish(task_id: str, user_id: str):
    """Simulate publishing progress with realistic delays and mock metrics."""
    import random
    from sqlalchemy import text as sql_text

    async with async_session() as db:
        try:
            stages = [
                (20, "上传视频中...", 1.5),
                (50, "转码处理中...", 2.0),
                (70, "平台审核中...", 2.0),
                (90, "发布中...", 1.0),
                (100, "发布成功", 0.5),
            ]
            for progress, msg, delay in stages:
                await asyncio.sleep(delay)
                await db.execute(sql_text(
                    "UPDATE publish_tasks SET progress=:p WHERE id=:id"
                ), {"p": progress, "id": task_id})
                await db.commit()

            # Generate mock metrics
            base_plays = random.randint(200, 5000)
            metrics = {
                "plays": base_plays,
                "likes": int(base_plays * random.uniform(0.02, 0.08)),
                "comments": int(base_plays * random.uniform(0.001, 0.01)),
                "shares": int(base_plays * random.uniform(0.002, 0.02)),
            }
            publish_result = {
                "platform_post_id": f"dy_{random.randint(10000000, 99999999)}",
                "publish_url": f"https://v.douyin.com/mock_{task_id[:8]}/",
                "published_at": now_cst().isoformat(),
            }
            await db.execute(sql_text(
                "UPDATE publish_tasks SET status='published', progress=100, publish_result=:pr, metrics=:m WHERE id=:id"
            ), {"pr": json.dumps(publish_result), "m": json.dumps(metrics), "id": task_id})
            await db.commit()
        except Exception as e:
            await db.execute(sql_text(
                "UPDATE publish_tasks SET status='failed', error_message=:msg WHERE id=:id"
            ), {"msg": str(e), "id": task_id})
            await db.commit()


async def _publish_scheduler():
    """Background scheduler: poll for due timed tasks every 30s and fire them."""
    from sqlalchemy import text as sql_text
    while True:
        try:
            await asyncio.sleep(30)
            async with async_session() as db:
                now = now_cst().isoformat()
                result = await db.execute(sql_text(
                    "SELECT id, user_id FROM publish_tasks WHERE status='pending' AND schedule_type='timed' AND schedule_time <= :now"
                ), {"now": now})
                due = result.fetchall()
                for row in due:
                    tid, uid = row[0], row[1]
                    print(f"[SCHEDULER] Firing scheduled publish task {tid[:8]}...")
                    asyncio.create_task(_simulate_publish(tid, uid))
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")


@app.post("/publish/reschedule/{task_id}")
async def reschedule_task(task_id: str, schedule_time: str, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    """Reschedule a pending timed publish task."""
    from sqlalchemy import text
    result = await db.execute(text(
        "UPDATE publish_tasks SET schedule_time=:st WHERE id=:id AND user_id=:uid AND status='pending'"
    ), {"st": schedule_time, "id": task_id, "uid": user["id"]})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(400, "任务不存在、不属于你或状态不是待发布")
    return {"ok": True, "id": task_id, "schedule_time": schedule_time}


@app.post("/publish/cancel/{task_id}")
async def cancel_publish_task(task_id: str, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    """Cancel a pending timed publish task."""
    from sqlalchemy import text
    result = await db.execute(text(
        "UPDATE publish_tasks SET status='cancelled' WHERE id=:id AND user_id=:uid AND status='pending'"
    ), {"id": task_id, "uid": user["id"]})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(400, "任务不存在、不属于你或状态不是待发布")
    return {"ok": True, "id": task_id}


@app.get("/publish/analytics")
async def publish_analytics(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    """Aggregate publish metrics for dashboard."""
    from sqlalchemy import text
    result = await db.execute(text(
        "SELECT status, metrics, schedule_type, platform_account_id, created_at FROM publish_tasks WHERE user_id=:uid"
    ), {"uid": user["id"]})
    rows = result.fetchall()
    import json

    total_plays = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    published_count = 0
    daily_map: dict[str, dict] = {}
    platform_map: dict[str, dict] = {}
    top_videos = []

    for r in rows:
        status, metrics_raw, stype, platform_id, created_at = r[0], r[1], r[2], r[3], r[4]
        m = json.loads(metrics_raw) if metrics_raw else {}
        plays = m.get("plays", 0) or 0
        likes = m.get("likes", 0) or 0
        comments = m.get("comments", 0) or 0
        shares = m.get("shares", 0) or 0

        if status == "published":
            published_count += 1
            total_plays += plays
            total_likes += likes
            total_comments += comments
            total_shares += shares

        # Daily trend (last 14 days by created_at date)
        if created_at:
            day = created_at[:10]  # "2026-07-14"
            if day not in daily_map:
                daily_map[day] = {"date": day, "publishes": 0, "plays": 0, "likes": 0}
            daily_map[day]["publishes"] += 1
            daily_map[day]["plays"] += plays
            daily_map[day]["likes"] += likes

        # Platform breakdown
        if platform_id:
            plat = platform_id[:3].upper()
            if plat not in platform_map:
                platform_map[plat] = {"platform": plat, "count": 0, "plays": 0, "likes": 0}
            platform_map[plat]["count"] += 1
            platform_map[plat]["plays"] += plays
            platform_map[plat]["likes"] += likes

        # Top videos
        top_videos.append({
            "task_id": r[0],
            "plays": plays,
            "likes": likes,
            "comments": comments,
            "shares": shares,
        })

    # Sort and limit
    top_videos.sort(key=lambda x: x["plays"], reverse=True)
    daily_trend = sorted(daily_map.values(), key=lambda x: x["date"])[-14:]
    platform_data = list(platform_map.values())

    return {
        "summary": {
            "total_publishes": published_count,
            "total_plays": total_plays,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "engagement_rate": round(total_likes / total_plays * 100, 2) if total_plays > 0 else 0,
        },
        "daily_trend": daily_trend,
        "platform_breakdown": platform_data,
        "top_videos": top_videos[:10],
    }


@app.get("/publish/analytics/export")
async def export_analytics(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    """Export publish analytics as CSV."""
    from sqlalchemy import text
    from fastapi.responses import StreamingResponse
    import io, csv as csv_module

    result = await db.execute(text(
        "SELECT id, video_url, platform_account_id, title, status, progress, schedule_type, schedule_time, metrics, publish_result, error_message, created_at FROM publish_tasks WHERE user_id=:uid ORDER BY created_at DESC"
    ), {"uid": user["id"]})
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv_module.writer(output)
    writer.writerow(["任务ID", "视频URL", "平台账号", "标题", "状态", "进度", "发布方式", "排期时间",
                      "播放量", "点赞", "评论", "分享", "发布时间", "错误信息", "创建时间"])

    for r in rows:
        m = json.loads(r[8]) if r[8] else {}
        pub = json.loads(r[9]) if r[9] else {}
        writer.writerow([
            r[0][:8], r[1], r[2], r[3], r[4], r[5], r[6], r[7] or '',
            m.get("plays", 0) or 0, m.get("likes", 0) or 0,
            m.get("comments", 0) or 0, m.get("shares", 0) or 0,
            pub.get("published_at", ''), r[10] or '', r[11],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
    )


# ============ Platform ============

class BindAccountReq(BaseModel):
    platform: str
    auth_token: str

@app.get("/platform/accounts")
async def list_accounts(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, platform, account_name, avatar, fans_count, auth_status, created_at FROM platform_accounts WHERE user_id = :uid"), {"uid": user["id"]})
    rows = result.fetchall()
    return [{"id": r[0], "platform": r[1], "account_name": r[2], "avatar": r[3], "fans_count": r[4], "auth_status": r[5], "created_at": r[6]} for r in rows]

@app.post("/platform/accounts/bind")
async def bind_account(req: BindAccountReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    aid = str(uuid.uuid4())
    now = now_cst().isoformat()
    await db.execute(text(
        "INSERT INTO platform_accounts (id, user_id, platform, account_name, auth_token, auth_status, created_at) VALUES (:id, :uid, :platform, :name, :token, 'active', :now)"
    ), {"id": aid, "uid": user["id"], "platform": req.platform, "name": f"{req.platform}_account", "token": req.auth_token, "now": now})
    await db.commit()
    return {"id": aid, "platform": req.platform, "account_name": f"{req.platform}_account", "avatar": None, "fans_count": 0, "auth_status": "active", "created_at": now}

@app.delete("/platform/accounts/{account_id}")
async def unbind_account(account_id: str, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM platform_accounts WHERE id = :id AND user_id = :uid"), {"id": account_id, "uid": user["id"]})
    await db.commit()
    return {"message": "已解绑"}

# ============ Payment ============

@app.get("/payment/plans")
async def list_plans():
    return [
        {"key": "free", "name": "免费版", "price": 0, "accounts": 1, "daily_videos": 3, "storage_gb": 1},
        {"key": "basic", "name": "基础版", "price": 9900, "accounts": 5, "daily_videos": 10, "storage_gb": 10},
        {"key": "pro", "name": "专业版", "price": 29900, "accounts": 20, "daily_videos": 50, "storage_gb": 50},
        {"key": "enterprise", "name": "企业版", "price": 99900, "accounts": 100, "daily_videos": 200, "storage_gb": 200},
    ]

class OrderReq(BaseModel):
    plan_key: str

@app.post("/payment/order")
async def create_order(req: OrderReq, user: dict = Depends(get_token_user)):
    import time
    order_id = f"PAY{int(time.time())}{uuid.uuid4().hex[:8].upper()}"
    plan_prices = {"free": 0, "basic": 99, "pro": 299, "enterprise": 999}
    return {"order_id": order_id, "plan": req.plan_key, "amount": plan_prices.get(req.plan_key, 99), "qr_code_url": ""}

# ============ Quota ============

@app.get("/quota/usage")
async def quota_usage(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT daily_video_count, monthly_video_count, account_limit, storage_bytes_used, storage_bytes_limit FROM user_quotas WHERE user_id = :uid"), {"uid": user["id"]})
    row = result.fetchone()
    if not row:
        return {"plan": "free", "plan_name": "免费版", "daily_edit": {"used": 0, "limit": 3}, "monthly_edit": {"used": 0, "limit": 30}, "accounts": {"used": 0, "limit": 1}, "storage": {"used": 0, "used_gb": 0, "limit": 1073741824, "limit_gb": 1.0}}

    # Count daily edit tasks (today in CST)
    today_start = now_cst().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    daily_res = await db.execute(text(
        "SELECT COUNT(*) FROM edit_tasks WHERE user_id = :uid AND created_at >= :today"
    ), {"uid": user["id"], "today": today_start})
    daily_used = daily_res.fetchone()[0]

    # Count monthly edit tasks
    month_start = now_cst().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    monthly_res = await db.execute(text(
        "SELECT COUNT(*) FROM edit_tasks WHERE user_id = :uid AND created_at >= :month"
    ), {"uid": user["id"], "month": month_start})
    monthly_used = monthly_res.fetchone()[0]

    # Count platform accounts
    acc_res = await db.execute(text(
        "SELECT COUNT(*) FROM platform_accounts WHERE user_id = :uid"
    ), {"uid": user["id"]})
    acc_used = acc_res.fetchone()[0]

    # Sum storage from materials table
    storage_res = await db.execute(text(
        "SELECT COALESCE(SUM(size), 0) FROM materials WHERE user_id = :uid"
    ), {"uid": user["id"]})
    storage_used = storage_res.fetchone()[0]

    plan_name = {"free": "免费版", "basic": "基础版", "pro": "专业版", "enterprise": "企业版"}.get(user.get("plan_type", "free"), "免费版")
    return {
        "plan": user.get("plan_type", "free"),
        "plan_name": plan_name,
        "daily_edit": {"used": daily_used, "limit": row[0]},
        "monthly_edit": {"used": monthly_used, "limit": row[1]},
        "accounts": {"used": acc_used, "limit": row[2]},
        "storage": {"used": storage_used, "used_gb": round(storage_used / (1024**3), 2), "limit": row[4], "limit_gb": round(row[4] / (1024**3), 1)},
    }

# ============ Feedback ============

class FeedbackReq(BaseModel):
    rating: int = 0
    content: str

@app.post("/feedback")
async def submit_feedback(req: FeedbackReq, user: dict = Depends(get_token_user)):
    return {"message": "反馈已收到，感谢！"}

# ============ Health ============

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

# ============ Startup ============

async def init_db():
    """Create all tables in SQLite."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, phone TEXT UNIQUE, password_hash TEXT,
            industry TEXT, company_name TEXT, plan_type TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_accounts (
            id TEXT PRIMARY KEY, user_id TEXT, platform TEXT, account_name TEXT,
            avatar TEXT, fans_count INTEGER DEFAULT 0, auth_token TEXT,
            auth_status TEXT DEFAULT 'pending', expired_at TEXT, created_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS material_folders (
            id TEXT PRIMARY KEY, user_id TEXT, name TEXT, parent_id TEXT, created_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY, user_id TEXT, folder_id TEXT, type TEXT,
            file_name TEXT, file_url TEXT, thumbnail_url TEXT, duration REAL,
            size INTEGER DEFAULT 0, tags TEXT, created_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS copywriting_templates (
            id TEXT PRIMARY KEY, user_id TEXT, title TEXT, body TEXT, tags TEXT,
            style TEXT, source TEXT DEFAULT 'ai', source_url TEXT,
            is_favorited INTEGER DEFAULT 0, created_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS edit_tasks (
            id TEXT PRIMARY KEY, user_id TEXT, material_ids TEXT, copywriting_id TEXT,
            template_id TEXT, params TEXT, status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0, output_urls TEXT, error_message TEXT,
            created_at TEXT, completed_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS publish_tasks (
            id TEXT PRIMARY KEY, user_id TEXT, video_url TEXT, platform_account_id TEXT,
            title TEXT, schedule_type TEXT, schedule_time TEXT,
            status TEXT DEFAULT 'pending', publish_result TEXT, metrics TEXT, created_at TEXT
        )"""))
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_quotas (
            id TEXT PRIMARY KEY, user_id TEXT UNIQUE, daily_video_count INTEGER DEFAULT 3,
            monthly_video_count INTEGER DEFAULT 30, account_limit INTEGER DEFAULT 1,
            storage_bytes_used INTEGER DEFAULT 0, storage_bytes_limit INTEGER DEFAULT 1073741824,
            updated_at TEXT
        )"""))
    print("SQLite 数据库已初始化 (aihuoke.db)")

if __name__ == "__main__":
    import uvicorn
    asyncio.run(init_db())
    # Start publish scheduler in background daemon thread
    import threading
    def _run_scheduler():
        asyncio.run(_publish_scheduler())
    threading.Thread(target=_run_scheduler, daemon=True).start()

    print("本地服务器启动: http://localhost:8000")
    print("验证码: 8888")
    uvicorn.run(app, host="0.0.0.0", port=8000)
