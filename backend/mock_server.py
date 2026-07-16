"""
轻量Mock API服务器 — 无需数据库，用于前端开发和演示。
启动: python mock_server.py
"""
import uuid
import time
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
codes = {}
users = {}
tasks = []
materials = []
accounts = []
copywritings = []

# ============ Auth ============

class SendCodeReq(BaseModel):
    phone: str

class LoginReq(BaseModel):
    phone: str
    code: str

@app.post("/auth/send-code")
def send_code(req: SendCodeReq):
    codes[req.phone] = "8888"
    return {"message": "验证码已发送", "debug_code": "8888"}

@app.post("/auth/login")
def login(req: LoginReq):
    if codes.get(req.phone) != req.code:
        return {"detail": "验证码错误"}, 400
    uid = str(uuid.uuid4())
    token = f"mock_token_{uid[:8]}"
    users[token] = {
        "id": uid, "phone": req.phone,
        "industry": None, "company_name": None,
        "plan_type": "free",
    }
    del codes[req.phone]
    return {"access_token": token, "token_type": "bearer"}

def get_user_from_token(auth_header: str | None):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return users.get(token)

@app.get("/auth/me")
def get_me(authorization: str | None = None):
    user = get_user_from_token(authorization)
    if not user:
        return {"detail": "Invalid token"}, 401
    return user

@app.put("/auth/profile")
def update_profile(req: dict, authorization: str | None = None):
    user = get_user_from_token(authorization)
    if not user:
        return {"detail": "Invalid token"}, 401
    if "industry" in req:
        user["industry"] = req["industry"]
    if "company_name" in req:
        user["company_name"] = req["company_name"]
    return user

# ============ Content ============

@app.get("/content/copywriting/list")
def list_copywriting(authorization: str | None = None):
    user = get_user_from_token(authorization)
    if not user:
        return []
    now = datetime.utcnow().isoformat()
    return [
        {"id": "cw1", "title": "重庆火锅 — 正宗牛油锅底", "body": "在重庆，没有一顿火锅解决不了的事！\n\n我们家的锅底，用了28味中草药和上等牛油，熬足8小时。看这翻滚的红汤，光闻着就流口水了吧？\n\n必点菜品：鲜毛肚，七上八下15秒，蘸上香油蒜泥，一口下去那个脆嫩……绝了！\n\n现在团购价只要128元，2-3人吃到撑。", "tags": "#重庆火锅 #火锅探店 #美食", "style": "口播", "source": "ai", "is_favorited": False, "created_at": now},
        {"id": "cw2", "title": "夏天必喝的爆款柠檬茶", "body": "30秒教会你做一杯好喝到爆的暴打柠檬茶！\n\n新鲜香水柠檬切片，一定要用香水柠檬。加冰暴打，把柠檬的香气打出来。倒入秘制茶底，一杯成本不到3块，卖15块！", "tags": "#柠檬茶 #饮品教程 #创业", "style": "教程", "source": "ai", "is_favorited": True, "created_at": now},
        {"id": "cw3", "title": "99元体验韩国明星同款皮肤管理", "body": "姐妹们，这家藏在写字楼里的宝藏皮肤管理店，我不允许还有人不知道！\n\n韩国进口仪器，院长10年经验。99元体验包含深层清洁、玻尿酸导入、LED光疗、补水面膜。全程60分钟无推销。", "tags": "#皮肤管理 #美容院探店", "style": "展示", "source": "ai", "is_favorited": False, "created_at": now},
    ]

@app.post("/content/copywriting/generate")
def generate_copywriting(req: dict, authorization: str | None = None):
    return {"message": "generated"}

@app.post("/content/copywriting/parse-link")
def parse_link(req: dict, authorization: str | None = None):
    return {"title_formula": "痛点+解决方案+优惠", "body_structure": "开场3秒抓眼球→展示产品→价格锚点→限时优惠→引导行动", "tag_strategy": "#行业词 #场景词 #热搜词", "key_elements": "1.夸张开场 2.价格对比 3.紧迫感 4.行动指令"}

@app.get("/content/materials")
def list_materials(authorization: str | None = None):
    return materials

@app.get("/content/folders")
def list_folders(authorization: str | None = None):
    return [{"id": "f1", "name": "产品展示", "parent_id": None, "created_at": datetime.utcnow().isoformat()},
            {"id": "f2", "name": "门店环境", "parent_id": None, "created_at": datetime.utcnow().isoformat()}]

@app.post("/content/folders")
def create_folder(req: dict, authorization: str | None = None):
    return {"id": str(uuid.uuid4()), "name": req.get("name", ""), "parent_id": req.get("parent_id"), "created_at": datetime.utcnow().isoformat()}

@app.get("/content/edit-tasks")
def list_edit_tasks(authorization: str | None = None):
    now = datetime.utcnow().isoformat()
    return [
        {"id": "t1", "material_ids": ["m1", "m2", "m3"], "copywriting_id": "cw1", "template_id": "mix", "status": "done", "progress": 100, "output_urls": ["/videos/output_001.mp4"], "error_message": None, "created_at": now},
        {"id": "t2", "material_ids": ["m4", "m5", "m6", "m7"], "copywriting_id": "cw2", "template_id": "fast_cut", "status": "processing", "progress": 65, "output_urls": [], "error_message": None, "created_at": now},
    ]

@app.post("/content/edit-tasks")
def create_edit_task(req: dict, authorization: str | None = None):
    return {"id": str(uuid.uuid4()), "status": "pending", "progress": 0, "output_urls": [], "created_at": datetime.utcnow().isoformat()}

# ============ Publish ============

@app.get("/publish/tasks")
def list_publish_tasks(authorization: str | None = None):
    now = datetime.utcnow().isoformat()
    return [
        {"id": "p1", "video_url": "/videos/output_001.mp4", "platform_account_id": "a1", "title": "重庆火锅探店", "schedule_type": "now", "schedule_time": None, "status": "published", "publish_result": {"status": "published"}, "metrics": {"plays": 12500, "likes": 856, "comments": 123, "shares": 45}, "created_at": now},
        {"id": "p2", "video_url": "/videos/output_002.mp4", "platform_account_id": "a1", "title": "夏季饮品教程", "schedule_type": "timed", "schedule_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(), "status": "pending", "publish_result": None, "metrics": {}, "created_at": now},
    ]

@app.post("/publish/tasks")
def create_publish_task(req: dict, authorization: str | None = None):
    return {"id": str(uuid.uuid4()), "status": "published", "metrics": {}, "created_at": datetime.utcnow().isoformat()}

# ============ Platform ============

@app.get("/platform/accounts")
def list_accounts(authorization: str | None = None):
    now = datetime.utcnow().isoformat()
    return [
        {"id": "a1", "platform": "douyin", "account_name": "重庆火锅王老板", "avatar": None, "fans_count": 12500, "auth_status": "active", "created_at": now},
    ]

@app.post("/platform/accounts/bind")
def bind_account(req: dict, authorization: str | None = None):
    return {"id": str(uuid.uuid4()), "platform": req.get("platform", "douyin"), "account_name": f"{req.get('platform')}_account", "avatar": None, "fans_count": 0, "auth_status": "active", "created_at": datetime.utcnow().isoformat()}

# ============ OAuth (Mock) ============

@app.get("/platform/oauth/douyin/authorize")
def douyin_authorize(authorization: str | None = None):
    """Mock Douyin OAuth authorize — returns a simulated authorization URL."""
    user = get_user_from_token(authorization)
    if not user:
        return {"detail": "Invalid token"}, 401
    state = f"mock_state_{uuid.uuid4().hex[:16]}"
    authorize_url = f"http://localhost:8000/platform/oauth/douyin/callback?code=mock_code_{uuid.uuid4().hex}&state={state}"
    return {"authorize_url": authorize_url, "state": state}

@app.get("/platform/oauth/douyin/callback")
def douyin_callback(code: str, state: str):
    """Mock Douyin OAuth callback — simulates successful authorization."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"http://localhost:5173/oauth/callback?bind_status=success&platform=douyin")

# ============ Payment ============

@app.get("/payment/plans")
def list_plans():
    return [
        {"key": "free", "name": "免费版", "price": 0, "accounts": 1, "daily_videos": 3, "storage_gb": 1},
        {"key": "basic", "name": "基础版", "price": 9900, "accounts": 5, "daily_videos": 10, "storage_gb": 10},
        {"key": "pro", "name": "专业版", "price": 29900, "accounts": 20, "daily_videos": 50, "storage_gb": 50},
        {"key": "enterprise", "name": "企业版", "price": 99900, "accounts": 100, "daily_videos": 200, "storage_gb": 200},
    ]

@app.post("/payment/order")
def create_order(req: dict, authorization: str | None = None):
    return {"order_id": f"PAY{int(time.time())}", "plan": req.get("plan_key"), "amount": 99.0, "qr_code_url": ""}

# ============ Quota ============

@app.get("/quota/usage")
def quota_usage(authorization: str | None = None):
    return {
        "plan": "free", "plan_name": "免费版",
        "daily_edit": {"used": 2, "limit": 3},
        "monthly_edit": {"used": 12, "limit": 30},
        "accounts": {"used": 1, "limit": 1},
        "storage": {"used": 157286400, "used_gb": 0.15, "limit": 1073741824, "limit_gb": 1.0},
    }

# ============ Feedback ============

@app.post("/feedback")
def submit_feedback(req: dict, authorization: str | None = None):
    return {"message": "反馈已收到"}

# ============ Health ============

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0-mock"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    print("Mock server running at http://localhost:8000")
