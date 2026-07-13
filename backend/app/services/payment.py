"""
WeChat Pay integration for subscription billing.
"""
import hashlib
import time
import uuid


PLANS = {
    "free": {"name": "免费版", "price": 0, "accounts": 1, "daily_videos": 3, "storage_gb": 1},
    "basic": {"name": "基础版", "price": 9900, "accounts": 5, "daily_videos": 10, "storage_gb": 10},
    "pro": {"name": "专业版", "price": 29900, "accounts": 20, "daily_videos": 50, "storage_gb": 50},
    "enterprise": {"name": "企业版", "price": 99900, "accounts": 100, "daily_videos": 200, "storage_gb": 200},
}


def get_all_plans() -> list[dict]:
    return [{"key": k, **v} for k, v in PLANS.items()]


def create_order(user_id: str, plan_key: str) -> dict:
    """Create a WeChat Pay order for subscription."""
    if plan_key not in PLANS:
        raise ValueError(f"Unknown plan: {plan_key}")

    plan = PLANS[plan_key]
    order_id = f"PAY{int(time.time())}{uuid.uuid4().hex[:8].upper()}"

    # In production: call WeChat Pay API to create prepay_id
    return {
        "order_id": order_id,
        "plan": plan_key,
        "amount": plan["price"] / 100,  # convert to yuan
        "qr_code_url": f"https://api.example.com/pay/{order_id}",  # placeholder
    }


def handle_callback(data: dict) -> dict:
    """Handle WeChat Pay payment callback."""
    # In production: verify signature, update user plan
    order_id = data.get("out_trade_no", "")
    return {"order_id": order_id, "status": "paid"}
