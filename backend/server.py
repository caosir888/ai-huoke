"""
本地开发服务器 — 使用 SQLite，无需安装任何数据库。
启动: python server.py
"""
import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta

# Patch config to use SQLite before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./aihuoke.db"

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
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
        ), {"id": uid, "phone": req.phone, "industry": None, "company": None, "now": datetime.utcnow().isoformat()})
        # Init quota
        await db.execute(text(
            "INSERT INTO user_quotas (id, user_id, daily_video_count, monthly_video_count, account_limit, storage_bytes_used, storage_bytes_limit, updated_at) "
            "VALUES (:id, :uid, 3, 30, 1, 0, 1073741824, :now)"
        ), {"id": str(uuid.uuid4()), "uid": uid, "now": datetime.utcnow().isoformat()})
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

class ParseLinkReq(BaseModel):
    url: str

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
        now = datetime.utcnow().isoformat()
        return [
            {"id": "demo1", "title": "重庆火锅 — 正宗牛油锅底", "body": "在重庆，没有一顿火锅解决不了的事！\n\n我们家的锅底，用了28味中草药和上等牛油，熬足8小时。看这翻滚的红汤，光闻着就流口水了吧？\n\n必点菜品：鲜毛肚，七上八下15秒，蘸上香油蒜泥，一口下去那个脆嫩……绝了！\n\n现在团购价只要128元，2-3人吃到撑。", "tags": "#重庆火锅 #火锅探店", "style": "口播", "source": "ai", "is_favorited": False, "created_at": now},
            {"id": "demo2", "title": "夏天必喝的爆款柠檬茶", "body": "30秒教会你做一杯好喝到爆的暴打柠檬茶！🍋\n\n新鲜香水柠檬切片，加冰暴打，把柠檬的香气打出来。倒入秘制茶底，一杯成本不到3块，卖15块！\n\n想了解更多饮品配方，关注我下期分享。", "tags": "#柠檬茶 #饮品教程", "style": "教程", "source": "ai", "is_favorited": True, "created_at": now},
            {"id": "demo3", "title": "99元体验韩国明星同款皮肤管理", "body": "姐妹们，这家藏在写字楼里的宝藏皮肤管理店！\n\n韩国进口仪器，院长10年经验。99元体验：深层清洁+玻尿酸导入+LED光疗+补水面膜。全程60分钟无推销。", "tags": "#皮肤管理 #美容院探店", "style": "展示", "source": "ai", "is_favorited": False, "created_at": now},
        ]
    return [{"id": r[0], "title": r[1], "body": r[2], "tags": r[3], "style": r[4], "source": r[5], "is_favorited": bool(r[6]), "created_at": r[7]} for r in rows]

@app.post("/content/copywriting/generate")
async def generate_copywriting(req: GenerateCopywritingReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    now = datetime.utcnow().isoformat()
    generated = []
    for i in range(req.count):
        cid = str(uuid.uuid4())
        await db.execute(text(
            "INSERT INTO copywriting_templates (id, user_id, title, body, tags, style, source, is_favorited, created_at) VALUES (:id, :uid, :title, :body, :tags, :style, 'ai', 0, :now)"
        ), {"id": cid, "uid": user["id"], "title": f"{req.keywords}文案{i+1}", "body": f"关于{req.keywords}的精彩文案内容...（接入DeepSeek后生成真实内容）", "tags": f"#{req.keywords}", "style": req.style, "now": now})
        generated.append({"id": cid, "title": f"{req.keywords}文案{i+1}", "body": "...", "tags": f"#{req.keywords}", "style": req.style, "source": "ai", "is_favorited": False, "created_at": now})
    await db.commit()
    return generated

@app.post("/content/copywriting/parse-link")
async def parse_link(req: ParseLinkReq, user: dict = Depends(get_token_user)):
    return {"title_formula": "痛点+解决方案+优惠", "body_structure": "开场3秒抓眼球→展示产品→价格锚点→限时优惠→引导行动", "tag_strategy": "#行业词 #场景词", "key_elements": "1.夸张开场 2.价格对比 3.紧迫感 4.行动指令"}

@app.post("/content/materials/upload")
async def upload_material(file: UploadFile = File(...), folder_id: str | None = Form(None), user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    mid = str(uuid.uuid4())
    file_url = f"/uploads/{user['id']}/{file.filename}"
    now = datetime.utcnow().isoformat()
    await db.execute(text(
        "INSERT INTO materials (id, user_id, folder_id, type, file_name, file_url, size, duration, tags, created_at) VALUES (:id, :uid, :fid, :type, :name, :url, :size, :dur, '{}', :now)"
    ), {"id": mid, "uid": user["id"], "fid": folder_id, "type": "video", "name": file.filename, "url": file_url, "size": file.size or 0, "dur": None, "now": now})
    await db.commit()
    return {"id": mid, "type": "video", "file_name": file.filename, "file_url": file_url, "thumbnail_url": None, "duration": None, "size": file.size or 0, "tags": [], "created_at": now}

@app.get("/content/materials")
async def list_materials(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, type, file_name, file_url, thumbnail_url, duration, size, tags, created_at FROM materials WHERE user_id = :uid ORDER BY created_at DESC LIMIT 100"), {"uid": user["id"]})
    rows = result.fetchall()
    return [{"id": r[0], "type": r[1], "file_name": r[2], "file_url": r[3], "thumbnail_url": r[4], "duration": r[5], "size": r[6], "tags": r[7].split(",") if isinstance(r[7], str) else [], "created_at": r[8]} for r in rows]

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
    now = datetime.utcnow().isoformat()
    await db.execute(text("INSERT INTO material_folders (id, user_id, name, parent_id, created_at) VALUES (:id, :uid, :name, :pid, :now)"), {"id": fid, "uid": user["id"], "name": req.name, "pid": req.parent_id, "now": now})
    await db.commit()
    return {"id": fid, "name": req.name, "parent_id": req.parent_id, "created_at": now}

@app.post("/content/edit-tasks")
async def create_edit_task(req: CreateEditTaskReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute(text("INSERT INTO edit_tasks (id, user_id, material_ids, copywriting_id, template_id, params, status, progress, output_urls, created_at) VALUES (:id, :uid, :mids, :cid, :tid, :params, 'pending', 0, '{}', :now)"), {"id": tid, "uid": user["id"], "mids": ",".join(req.material_ids), "cid": req.copywriting_id, "tid": req.template_id, "params": req.model_dump_json(), "now": now})
    await db.commit()
    return {"id": tid, "material_ids": req.material_ids, "status": "pending", "progress": 0, "output_urls": [], "error_message": None, "created_at": now}

@app.get("/content/edit-tasks")
async def list_edit_tasks(user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, material_ids, status, progress, output_urls, error_message, created_at FROM edit_tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 50"), {"uid": user["id"]})
    rows = result.fetchall()
    return [{"id": r[0], "material_ids": r[1].split(",") if isinstance(r[1], str) else [], "status": r[2], "progress": r[3], "output_urls": r[4].split(",") if isinstance(r[4], str) and r[4] else [], "error_message": r[5], "created_at": r[6]} for r in rows]

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
    result = await db.execute(text("SELECT id, video_url, platform_account_id, title, schedule_type, schedule_time, status, publish_result, metrics, created_at FROM publish_tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 100"), {"uid": user["id"]})
    rows = result.fetchall()
    import json
    return [{"id": r[0], "video_url": r[1], "platform_account_id": r[2], "title": r[3], "schedule_type": r[4], "schedule_time": r[5], "status": r[6], "publish_result": json.loads(r[7]) if r[7] else None, "metrics": json.loads(r[8]) if r[8] else {}, "created_at": r[9]} for r in rows]

@app.post("/publish/tasks")
async def create_publish_task(req: CreatePublishTaskReq, user: dict = Depends(get_token_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    import json
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute(text(
        "INSERT INTO publish_tasks (id, user_id, video_url, platform_account_id, title, schedule_type, schedule_time, status, metrics, created_at) VALUES (:id, :uid, :url, :aid, :title, :st, :sch, 'published', :metrics, :now)"
    ), {"id": tid, "uid": user["id"], "url": req.video_url, "aid": req.platform_account_id, "title": req.title, "st": req.schedule_type, "sch": req.schedule_time, "metrics": json.dumps({"plays": 0, "likes": 0, "comments": 0, "shares": 0}), "now": now})
    await db.commit()
    return {"id": tid, "video_url": req.video_url, "platform_account_id": req.platform_account_id, "title": req.title, "schedule_type": req.schedule_type, "schedule_time": req.schedule_time, "status": "published", "publish_result": None, "metrics": {}, "created_at": now}

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
    now = datetime.utcnow().isoformat()
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
    if row:
        return {
            "plan": user.get("plan_type", "free"), "plan_name": {"free": "免费版", "basic": "基础版", "pro": "专业版", "enterprise": "企业版"}.get(user.get("plan_type", "free"), "免费版"),
            "daily_edit": {"used": 0, "limit": row[0]},
            "monthly_edit": {"used": 0, "limit": row[1]},
            "accounts": {"used": 0, "limit": row[2]},
            "storage": {"used": row[3], "used_gb": round(row[3]/(1024**3), 2), "limit": row[4], "limit_gb": round(row[4]/(1024**3), 1)},
        }
    return {"plan": "free", "plan_name": "免费版", "daily_edit": {"used": 0, "limit": 3}, "monthly_edit": {"used": 0, "limit": 30}, "accounts": {"used": 0, "limit": 1}, "storage": {"used": 0, "used_gb": 0, "limit": 1073741824, "limit_gb": 1.0}}

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
            monthly_video_count INTEGER DEFAULT 90, account_limit INTEGER DEFAULT 1,
            storage_bytes_used INTEGER DEFAULT 0, storage_bytes_limit INTEGER DEFAULT 1073741824,
            updated_at TEXT
        )"""))
    print("SQLite 数据库已初始化 (aihuoke.db)")

if __name__ == "__main__":
    import uvicorn
    asyncio.run(init_db())
    print("本地服务器启动: http://localhost:8000")
    print("验证码: 8888")
    uvicorn.run(app, host="0.0.0.0", port=8000)
