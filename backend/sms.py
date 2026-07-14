"""
SMS verification code module.
Supports debug mode (console print) and Alibaba Cloud SMS (production).
Configure via environment variables:
  SMS_PROVIDER=debug|aliyun  (default: debug)
  ALIYUN_ACCESS_KEY_ID       (required for aliyun)
  ALIYUN_ACCESS_KEY_SECRET   (required for aliyun)
  ALIYUN_SMS_SIGN_NAME       (required for aliyun)
  ALIYUN_SMS_TEMPLATE_CODE   (required for aliyun, e.g. SMS_123456789)
"""
import os
import time
import random
import hashlib
import hmac
import urllib.parse
import urllib.request
import uuid as _uuid
from datetime import datetime

# In-memory rate limiting and code storage
_codes: dict[str, tuple[str, float]] = {}    # phone -> (code, expiry_timestamp)
_last_send: dict[str, float] = {}            # phone -> last send timestamp
RATE_LIMIT_SECONDS = 60
CODE_EXPIRE_SECONDS = 300  # 5 minutes
CODE_LENGTH = 6


def generate_code() -> str:
    return str(random.randint(10**(CODE_LENGTH-1), 10**CODE_LENGTH - 1))


def can_send(phone: str) -> bool:
    """Check if enough time has passed since last send to this phone."""
    last = _last_send.get(phone, 0)
    return (time.time() - last) >= RATE_LIMIT_SECONDS


def seconds_until_next(phone: str) -> int:
    """Seconds remaining before this phone can send again."""
    last = _last_send.get(phone, 0)
    elapsed = time.time() - last
    return max(0, int(RATE_LIMIT_SECONDS - elapsed))


def store_code(phone: str, code: str):
    """Store verification code with expiry for a phone number."""
    _codes[phone] = (code, time.time() + CODE_EXPIRE_SECONDS)
    _last_send[phone] = time.time()


def verify_code(phone: str, code: str) -> tuple[bool, str]:
    """Verify a code. Returns (valid, error_message)."""
    stored = _codes.get(phone)
    if stored is None:
        return False, "请先发送验证码"
    expected, expiry = stored
    if time.time() > expiry:
        del _codes[phone]
        return False, "验证码已过期，请重新发送"
    if code != expected:
        return False, "验证码错误"
    del _codes[phone]
    return True, ""


def send_sms(phone: str, code: str) -> dict:
    """
    Send SMS via configured provider.
    Returns {"ok": bool, "debug_code": str|None, "error": str|None}
    """
    provider = os.getenv("SMS_PROVIDER", "debug")
    if provider == "aliyun":
        return _send_aliyun(phone, code)
    return _send_debug(phone, code)


def _send_debug(phone: str, code: str) -> dict:
    """Debug mode: print to console, always succeed."""
    print(f"\n{'='*50}")
    print(f"[SMS-DEBUG] 验证码发送到 {phone}")
    print(f"[SMS-DEBUG] 验证码: {code}")
    print(f"{'='*50}\n")
    return {"ok": True, "debug_code": code, "error": None}


def _send_aliyun(phone: str, code: str) -> dict:
    """
    Send SMS via Alibaba Cloud SMS API.
    Uses API v2 signature (HMAC-SHA1).
    Docs: https://help.aliyun.com/document_detail/419273.html
    """
    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
    sign_name = os.getenv("ALIYUN_SMS_SIGN_NAME", "")
    template_code = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "")

    if not all([access_key_id, access_key_secret, sign_name, template_code]):
        print("[SMS-ALIYUN] Missing credentials, falling back to debug mode")
        return _send_debug(phone, code)

    params = {
        "AccessKeyId": access_key_id,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "SignName": sign_name,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": _uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "TemplateCode": template_code,
        "TemplateParam": f'{{"code":"{code}"}}',
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }

    # Build canonical query string for signing
    sorted_params = sorted(params.items())
    query_string = urllib.parse.urlencode(sorted_params)
    string_to_sign = "GET&%2F&" + urllib.parse.quote(query_string, safe="")

    signature = hmac.new(
        (access_key_secret + "&").encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1
    ).digest()
    import base64
    params["Signature"] = base64.b64encode(signature).decode("utf-8")

    url = "https://dysmsapi.aliyuncs.com/?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode("utf-8")
        print(f"[SMS-ALIYUN] Response: {body[:200]}")
        # Parse JSON response
        import json
        result = json.loads(body)
        if result.get("Code") == "OK":
            return {"ok": True, "debug_code": None, "error": None}
        err = result.get("Message", "短信发送失败")
        print(f"[SMS-ALIYUN] Failed: {err}")
        return {"ok": False, "debug_code": None, "error": err}
    except Exception as e:
        print(f"[SMS-ALIYUN] Exception: {e}")
        return {"ok": False, "debug_code": None, "error": str(e)}
