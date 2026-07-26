import requests
import json
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
    
    def initialize_payment(self, email: str, amount_pesewas: int, user_id: int, bot_name: str) -> Optional[Dict]:
        """Initialize a payment transaction"""
        
        payload = {
            "email": email,
            "amount": amount_pesewas,  # Amount in pesewas (50 GHS = 5000 pesewas)
            "metadata": {
                "user_id": user_id,
                "bot_name": bot_name,
                "type": "bot_clone"
            }
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
                
                return {
                    "status": "success" if payment_data.get("status") == "success" else "failed",
                    "reference": payment_data.get("reference"),
                    "amount": payment_data.get("amount"),
                    "customer": payment_data.get("customer", {}),
                    "metadata": payment_data.get("metadata", {}),
                    "paid_at": payment_data.get("paid_at")
                }
        except Exception as e:
            print(f"[v0] Payment verification error: {e}")
        
        return {"status": "error", "message": "Failed to verify payment"}
    
    def verify_webhook(self, request_body: str, signature: str) -> bool:
        """Verify Paystack webhook signature"""
        
        hash_object = hmac.new(
            self.secret_key.encode('utf-8'),
            request_body.encode('utf-8'),
            hashlib.sha512
        )
        
        expected_signature = hash_object.hexdigest()
        return signature == expected_signature
    
    def create_payment_link(self, email: str, amount_ghs: int, user_id: int, bot_name: str) -> Optional[str]:
        """Create a Paystack payment link for the bot clone"""
        
        amount_pesewas = amount_ghs * 100  # Convert GHS to pesewas
        result = self.initialize_payment(email, amount_pesewas, user_id, bot_name)
        
        if result.get("status") == "success":
            return result.get("authorization_url")
        
        return None
    
    def get_payment_status(self, reference: str) -> str:
        """Get payment status"""
        result = self.verify_payment(reference)
        return result.get("status", "unknown")

class StripeCommission:
    """Handle Stripe payment processing for cloned bots and commission tracking"""
    
    def __init__(self):
        self.api_key = None  # User provides their own Stripe key
        self.commission_rate = 0.10  # 10% commission to main bot owner
    
    def initialize_payment(self, stripe_key: str, amount_cents: int, user_id: int, 
                          description: str, metadata: Dict = None) -> Optional[Dict]:
        """Initialize Stripe payment using user's Stripe key"""
        try:
            import stripe
            stripe.api_key = stripe_key
            
            payload = {
                "amount": amount_cents,
                "currency": "ghs",
                "description": description,
                "metadata": metadata or {"user_id": user_id}
            }
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(**payload)
            
            return {
                "status": "success",
                "client_secret": intent.get("client_secret"),
                "payment_intent_id": intent.get("id"),
                "amount": intent.get("amount")
            }
        except Exception as e:
            print(f"[v0] Stripe initialization error: {e}")
            return {"status": "error", "message": str(e)}
    
    def verify_payment(self, stripe_key: str, payment_intent_id: str) -> Optional[Dict]:
        """Verify Stripe payment"""
        try:
            import stripe
            stripe.api_key = stripe_key
            
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "status": "success" if intent.get("status") == "succeeded" else "pending",
                "payment_intent_id": intent.get("id"),
                "amount": intent.get("amount"),
                "currency": intent.get("currency"),
                "metadata": intent.get("metadata", {})
            }
        except Exception as e:
            print(f"[v0] Stripe verification error: {e}")
            return {"status": "error", "message": str(e)}
    
    def calculate_commission(self, amount_cents: int) -> Dict:
        """Calculate commission split"""
        commission = int(amount_cents * self.commission_rate)
        cloned_bot_owner = amount_cents - commission
        
        return {
            "total_amount": amount_cents,
            "main_bot_commission": commission,
            "cloned_bot_owner_receives": cloned_bot_owner,
            "commission_percentage": self.commission_rate * 100
        }
    
    def track_commission(self, cloned_bot_id: int, payment_amount: int, 
                        stripe_key_id: str, payment_intent_id: str) -> bool:
        """Track commission in database"""
        try:
            from database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            split = self.calculate_commission(payment_amount)
            
            cursor.execute(
                """INSERT INTO commission_tracking 
                   (cloned_bot_id, payment_amount, main_commission, owner_amount, 
                    stripe_key_id, payment_intent_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (cloned_bot_id, payment_amount, split["main_bot_commission"],
                 split["cloned_bot_owner_receives"], stripe_key_id, payment_intent_id)
            )
            
            db.commit()
            db.close()
            return True
        except Exception as e:
            print(f"[v0] Commission tracking error: {e}")
            return False
    
    def get_commission_stats(self, cloned_bot_id: int) -> Dict:
        """Get commission statistics for a cloned bot"""
        try:
            from database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            cursor.execute(
                """SELECT SUM(owner_amount), COUNT(*), SUM(payment_amount) 
                   FROM commission_tracking WHERE cloned_bot_id = ?""",
                (cloned_bot_id,)
            )
            
            result = cursor.fetchone()
            db.close()
            
            if result and result[0]:
                return {
                    "total_owner_earnings": result[0],
                    "total_transactions": result[1] or 0,
                    "total_revenue": result[2] or 0
                }
            
            return {"total_owner_earnings": 0, "total_transactions": 0, "total_revenue": 0}
        except Exception as e:
            print(f"[v0] Error fetching commission stats: {e}")
            return {}


# Global instances
paystack = PaystackPayment()
stripe_commission = StripeCommission()
