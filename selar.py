"""Selar checkout configuration and webhook field normalization."""
import os
from typing import Any, Dict, Optional


def checkout_url(payment_type: str, clone_id: int = 0) -> Optional[str]:
    """Return the configured Selar checkout URL for a trusted product."""
    key = {
        "bot_clone": "SELAR_CLONE_CHECKOUT_URL",
        "utility_subscription": "SELAR_UTILITY_CHECKOUT_URL",
        "ai_subscription": "SELAR_AI_CHECKOUT_URL",
        "image_search_unlock": "SELAR_IMAGE_SEARCH_CHECKOUT_URL",
        "premium_group": "SELAR_PREMIUM_GROUP_CHECKOUT_URL",
        "clone_monetization": "SELAR_CLONE_MONETIZATION_CHECKOUT_URL",
        "botstore_premium": "SELAR_BOTSTORE_PREMIUM_CHECKOUT_URL",
        "superbot_tier": "SELAR_SUPERBOT_CHECKOUT_URL",
        "image_search_yandex": "SELAR_YANDEX_CHECKOUT_URL",
    }.get(payment_type)
    return os.getenv(key, "").strip() if key else None


def _first(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_sale(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize common Selar/Zapier payload shapes without trusting price."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    custom = data.get("custom_fields") or data.get("customFields") or data.get("answers") or {}
    if isinstance(custom, list):
        custom = {str(item.get("name", "")): item.get("value") for item in custom if isinstance(item, dict)}
    return {
        "sale_id": str(_first(data, "id", "sale_id", "order_id", "orderId", "reference", "transaction_id") or "").strip(),
        "product_id": str(_first(data, "product_id", "productId", "product_slug", "productSlug", "product_name", "productName", "item_name") or "").strip(),
        "product_name": str(_first(data, "product_name", "productName", "item_name", "name") or "").strip(),
        "email": str(_first(data, "email", "customer_email", "customerEmail") or "").strip().lower(),
        "telegram_user_id": _first(custom, os.getenv("SELAR_TELEGRAM_FIELD", "Telegram User ID"), "Telegram User ID", "telegram_user_id", "telegramUserId"),
        "clone_id": _first(custom, os.getenv("SELAR_CLONE_FIELD", "Clone ID"), "Clone ID", "clone_id", "cloneId"),
        "amount": _first(data, "amount", "total", "price"),
        "currency": str(_first(data, "currency", "currency_code") or "").upper(),
        "raw": data,
    }


def product_config(product_id: str, product_name: str) -> Optional[Dict[str, Any]]:
    """Map only configured Selar product IDs/slugs to entitlements."""
    candidates = {product_id.strip().lower(), product_name.strip().lower()}
    for key, entitlement in {
        "SELAR_PRODUCT_CLONE": "bot_clone",
        "SELAR_PRODUCT_AI": "ai_subscription",
        "SELAR_PRODUCT_UTILITY": "utility_subscription",
        "SELAR_PRODUCT_IMAGE_SEARCH": "image_search_unlock",
        "SELAR_PRODUCT_PREMIUM_GROUP": "premium_group",
        "SELAR_PRODUCT_CLONE_MONETIZATION": "clone_monetization",
        "SELAR_PRODUCT_BOTSTORE_PREMIUM": "botstore_premium",
        "SELAR_PRODUCT_SUPERBOT": "superbot_tier",
    }.items():
        configured = os.getenv(key, "").strip().lower()
        if configured and configured in candidates:
            return {"type": entitlement, "key": key}
    return None


class SelarPayment:
    """Checkout-only adapter; fulfillment happens exclusively by webhook."""
    def initialize_payment(self, email: str, amount_pesewas: int, user_id: int, bot_name: str, payment_type: str = "bot_clone", extra_metadata: Optional[Dict] = None):
        url = checkout_url(payment_type, int((extra_metadata or {}).get("clone_id", 0)))
        return {"status": "success", "reference": f"selar-pending-{user_id}", "authorization_url": url} if url else {"status": "error", "message": "Selar checkout URL is not configured"}

    def verify_payment(self, reference: str):
        return {"status": "pending", "message": "Selar confirms purchases through the webhook"}

selar = SelarPayment()


def valid_secret(headers: Dict[str, str], query_secret: str = "") -> bool:
    expected = os.getenv("SELAR_WEBHOOK_SECRET", "")
    supplied = headers.get("x-selar-webhook-secret") or headers.get("x-webhook-secret") or query_secret
    return bool(expected and supplied and supplied == expected)
