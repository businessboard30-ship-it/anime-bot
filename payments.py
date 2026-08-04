import requests
import hmac
import hashlib
from typing import Optional, Dict
from config import PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY

class PaystackPayment:
    """Handle Paystack payment processing"""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = PAYSTACK_SECRET_KEY
        self.public_key = PAYSTACK_PUBLIC_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_payment(self, email: str, amount_pesewas: int, user_id: int, bot_name: str, payment_type: str = "bot_clone", extra_metadata: Optional[Dict] = None, api_key: Optional[str] = None) -> Optional[Dict]:
        """Initialize a payment transaction.

        api_key: if given, overrides self.secret_key for this call only —
        used to route a clone's payment through the clone owner's own
        connected Paystack key instead of the main bot's account. Every
        other clone-scoped paywall call must pass this (see
        database.get_clone_payment_config)."""

        metadata = {
            "user_id": user_id,
            "bot_name": bot_name,
            "type": payment_type
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        payload = {
            "email": email,
            "amount": amount_pesewas,  # Amount in pesewas (50 GHS = 5000 pesewas)
            "currency": "GHS",
            "metadata": metadata
        }

        headers = self.headers if not api_key else {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "reference": data.get("data", {}).get("reference"),
                    "authorization_url": data.get("data", {}).get("authorization_url"),
                    "access_code": data.get("data", {}).get("access_code")
                }
            else:
                print(f"[v0] Paystack initialize failed: status={response.status_code} body={response.text[:500]}")
        except Exception as e:
            print(f"[v0] Paystack initialization error: {e}")
        
        return {"status": "error", "message": "Failed to initialize payment"}
    
    def verify_payment(self, reference: str, api_key: Optional[str] = None) -> Optional[Dict]:
        """Verify a payment transaction. Pass the same api_key used at
        initialize_payment time for a clone-routed payment — Paystack
        references are only valid against the key that created them."""

        headers = self.headers if not api_key else {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                payment_data = data.get("data", {})
                authorization = payment_data.get("authorization", {}) or {}
                
                return {
                    "status": "success" if payment_data.get("status") == "success" else "failed",
                    "reference": payment_data.get("reference"),
                    "amount": payment_data.get("amount"),
                    "customer": payment_data.get("customer", {}),
                    "metadata": payment_data.get("metadata", {}),
                    "paid_at": payment_data.get("paid_at"),
                    # Present when the card is reusable — needed to auto-charge
                    # future renewals without the user re-entering card details.
                    "authorization_code": authorization.get("authorization_code") if authorization.get("reusable") else None
                }
        except Exception as e:
            print(f"[v0] Payment verification error: {e}")
        
        return {"status": "error", "message": "Failed to verify payment"}

    def charge_authorization(self, authorization_code: str, email: str, amount_pesewas: int, reference: str = None, api_key: Optional[str] = None) -> Optional[Dict]:
        """Charge a previously-saved reusable card (recurring/auto-renewal billing),
        no re-entry of card details or redirect required."""
        payload = {
            "authorization_code": authorization_code,
            "email": email,
            "amount": amount_pesewas,
            "currency": "GHS"
        }
        if reference:
            payload["reference"] = reference

        headers = self.headers if not api_key else {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/charge_authorization",
                headers=headers,
                json=payload,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "status": "success" if data.get("status") == "success" else "failed",
                    "reference": data.get("reference")
                }
            print(f"[v0] Paystack charge_authorization failed: status={response.status_code} body={response.text[:500]}")
        except Exception as e:
            print(f"[v0] Paystack charge_authorization error: {e}")

        return {"status": "error", "message": "Failed to charge saved card"}
    
    def verify_webhook(self, request_body: str, signature: str) -> bool:
        """Verify Paystack webhook signature using constant-time comparison"""
        
        hash_object = hmac.new(
            self.secret_key.encode('utf-8'),
            request_body.encode('utf-8'),
            hashlib.sha512
        )
        
        expected_signature = hash_object.hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    
    def create_payment_link(self, email: str, amount_ghs: int, user_id: int, bot_name: str, payment_type: str = "bot_clone") -> Optional[str]:
        """Create a Paystack payment link"""
        
        amount_pesewas = amount_ghs * 100  # Convert GHS to pesewas
        result = self.initialize_payment(email, amount_pesewas, user_id, bot_name, payment_type)
        
        if result.get("status") == "success":
            return result.get("authorization_url")
        
        return None
    
    def get_payment_status(self, reference: str) -> str:
        """Get payment status"""
        result = self.verify_payment(reference)
        return result.get("status", "unknown")

class StripePayment:
    """Minimal Stripe Checkout client, used ONLY for clone owners who've
    connected their own Stripe secret key (handlers/clone_bot.py's Payment
    Settings menu) — there's no main-bot Stripe account, so every call here
    requires an api_key.

    IMPORTANT CURRENCY CAVEAT: the rest of this bot prices everything in
    GHS (Ghanaian Cedi). Stripe does not support GHS as a settlement/payout
    currency for most accounts. Rather than silently mis-billing a clone
    owner, amounts here are passed straight through as MINOR UNITS of
    whatever currency you configure (default USD) — the caller is
    responsible for converting the GHS price to that currency before
    calling this. This was not wired into any handler yet; do that
    conversion explicitly before enabling Stripe for a clone.
    """

    BASE_URL = "https://api.stripe.com/v1"

    def initialize_payment(self, email: str, amount_minor_units: int, user_id: int, bot_name: str,
                            payment_type: str = "bot_clone", extra_metadata: Optional[Dict] = None,
                            api_key: Optional[str] = None, currency: str = "usd",
                            success_url: str = "https://t.me", cancel_url: str = "https://t.me") -> Optional[Dict]:
        if not api_key:
            return {"status": "error", "message": "Stripe requires the clone owner's own secret key"}

        metadata = {"user_id": str(user_id), "bot_name": bot_name, "type": payment_type}
        if extra_metadata:
            metadata.update({k: str(v) for k, v in extra_metadata.items()})

        payload = {
            "mode": "payment",
            "customer_email": email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][price_data][currency]": currency,
            "line_items[0][price_data][product_data][name]": bot_name,
            "line_items[0][price_data][unit_amount]": amount_minor_units,
            "line_items[0][quantity]": 1,
        }
        for k, v in metadata.items():
            payload[f"metadata[{k}]"] = v

        try:
            response = requests.post(
                f"{self.BASE_URL}/checkout/sessions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=payload,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "reference": data.get("id"),
                    "authorization_url": data.get("url"),
                    "access_code": None
                }
            print(f"[v0] Stripe checkout session create failed: status={response.status_code} body={response.text[:500]}")
        except Exception as e:
            print(f"[v0] Stripe initialization error: {e}")

        return {"status": "error", "message": "Failed to initialize payment"}

    def verify_payment(self, reference: str, api_key: Optional[str] = None) -> Optional[Dict]:
        if not api_key:
            return {"status": "error", "message": "Stripe requires the clone owner's own secret key"}
        try:
            response = requests.get(
                f"{self.BASE_URL}/checkout/sessions/{reference}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                paid = data.get("payment_status") == "paid"
                return {
                    "status": "success" if paid else "failed",
                    "reference": data.get("id"),
                    "amount": data.get("amount_total"),
                    "customer": {"email": data.get("customer_email")},
                    "metadata": data.get("metadata", {}),
                    "paid_at": None,
                    "authorization_code": None,  # Stripe recurring billing needs its own Subscriptions setup, not wired here
                }
        except Exception as e:
            print(f"[v0] Stripe verification error: {e}")

        return {"status": "error", "message": "Failed to verify payment"}


# Global instances
paystack = PaystackPayment()
stripe_gateway = StripePayment()


async def resolve_gateway(clone_id: int):
    """Look up which gateway + key a payment for this clone should use.

    Returns (gateway_object, api_key_or_None, provider_str). clone_id=0
    (the main bot) and any clone that hasn't connected its own key both
    resolve to (paystack, None, "paystack") — i.e. the main bot's own
    Paystack account, same as before this existed.

    Call this at BOTH initialize and verify time (verify needs the same
    key that created the reference) — store the returned provider/api_key
    in context.user_data alongside the payment reference so verify can
    reuse them; don't re-resolve at verify time, since a clone owner could
    switch providers in between and break an in-flight payment.
    """
    if not clone_id:
        return paystack, None, "paystack"

    from database import db  # local import: avoids a database.py <-> payments.py import cycle
    cfg = await db.get_clone_payment_config(clone_id)
    provider = cfg.get("provider", "main")
    api_key = cfg.get("api_key")

    if provider == "paystack" and api_key:
        return paystack, api_key, "paystack"
    if provider == "stripe" and api_key:
        return stripe_gateway, api_key, "stripe"
    return paystack, None, "paystack"
