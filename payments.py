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
    
    def initialize_payment(self, email: str, amount_pesewas: int, user_id: int, bot_name: str, payment_type: str = "bot_clone", extra_metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Initialize a payment transaction"""
        
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
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=self.headers,
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
    
    def verify_payment(self, reference: str) -> Optional[Dict]:
        """Verify a payment transaction"""
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
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

    def charge_authorization(self, authorization_code: str, email: str, amount_pesewas: int, reference: str = None) -> Optional[Dict]:
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

        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/charge_authorization",
                headers=self.headers,
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

# Global instance
paystack = PaystackPayment()
