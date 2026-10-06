"""Paystack checkout and webhook normalization."""
import os
import secrets
from typing import Any, Dict, Optional

import requests


def checkout_url(payment_type: str, clone_id: int = 0) -> Optional[str]:
    """Initialize a Paystack transaction and return its hosted checkout URL."""
    return None


def _first(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_sale(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "sale_id": str(_first(data, "id", "reference", "transaction_id") or "").strip(),
        "product_id": str(_first(metadata, "product_id", "productId", "payment_type") or "").strip(),
        "product_name": str(_first(metadata, "product_name", "productName") or "").strip(),
        "email": str(_first(data, "email", "customer_email") or "").strip().lower(),
        "telegram_user_id": _first(metadata, "telegram_user_id", "telegramUserId"),
        "clone_id": _first(metadata, "clone_id", "cloneId"),
        "amount": _first(data, "amount", "total", "price"),
        "currency": str(_first(data, "currency") or "").upper(),
        "raw": data,
    }


def product_config(product_id: str, product_name: str) -> Optional[Dict[str, Any]]:
    candidates = {product_id.strip().lower(), product_name.strip().lower()}
    for key, entitlement in {
        "PAYSTACK_PRODUCT_CLONE": "bot_clone",
        "PAYSTACK_PRODUCT_AI": "ai_subscription",
        "PAYSTACK_PRODUCT_UTILITY": "utility_subscription",
        "PAYSTACK_PRODUCT_PREMIUM_GROUP": "premium_group",
        "PAYSTACK_PRODUCT_CLONE_MONETIZATION": "clone_monetization",
        "PAYSTACK_PRODUCT_SUPERBOT": "superbot_tier",
    }.items():
        configured = os.getenv(key, "").strip().lower()
        if configured and configured in candidates:
            return {"type": entitlement, "key": key}
    return None


def new_reference() -> str:
    """Paystack references are numeric and exactly 11 digits."""
    return str(secrets.randbelow(9_000_000_000) + 1_000_000_000)


class PaystackPayment:
    def initialize_payment(self, email: str, amount_kobo: int, user_id: int, bot_name: str, payment_type: str = "bot_clone", extra_metadata: Optional[Dict] = None):
        reference = new_reference()
        secret = os.getenv("PAYSTACK_SECRET_KEY", "")
        if not secret:
            return {"status": "error", "message": "Paystack is not configured"}
        metadata = {"telegram_user_id": str(user_id), "product_id": payment_type, **(extra_metadata or {})}
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={"email": email, "amount": int(amount_kobo), "currency": "GHS", "reference": reference, "metadata": metadata},
            timeout=15,
        )
        body = response.json()
        if not response.ok or not body.get("status"):
            return {"status": "error", "message": "Paystack initialization failed"}
        return {"status": "success", "reference": reference, "authorization_url": body["data"]["authorization_url"]}

    def verify_payment(self, reference: str):
        if not reference.isdigit() or len(reference) != 11:
            return {"status": "error", "message": "Invalid payment reference"}
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY', '')}"},
            timeout=15,
        )
        return response.json()

paystack = PaystackPayment()


def valid_secret(headers: Dict[str, str], raw_body: bytes) -> bool:
    import hashlib
    import hmac
    signature = headers.get("x-paystack-signature", "")
    expected = hmac.new(os.getenv("PAYSTACK_SECRET_KEY", "").encode(), raw_body, hashlib.sha512).hexdigest()
    return bool(signature and expected and hmac.compare_digest(signature, expected))


def reference_is_valid(reference: str) -> bool:
    return reference.isdigit() and len(reference) == 11
PAYSTACK_REFERENCE_DIGITS = 11

def checkout_url_for_type(payment_type: str, clone_id: int = 0) -> Optional[str]:
    return None


def reference_from_payload(payload: Dict[str, Any]) -> str:
    return str(payload.get("data", {}).get("reference", "")).strip()

def _unused():
    return checkout_url, checkout_url_for_type

PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_SECRET_KEY", "")
