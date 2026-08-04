"""
Paystack Webhook Handler for Payment Verification
Receives server-to-server payment confirmation from Paystack and activates features
"""

import json
import asyncio
from http.server import BaseHTTPRequestHandler
from payments import paystack
from database import db
from handlers.subscription import activate_subscription
import logging

logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    """Handle Paystack webhook events"""
    
    def do_POST(self):
        """Handle incoming Paystack webhook POST request"""
        
        # Read raw request body
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length).decode('utf-8')
        
        # Get signature header
        signature = self.headers.get('x-paystack-signature', '')
        
        # Verify signature using constant-time comparison
        if not paystack.verify_webhook(request_body, signature):
            logger.warning("[v0] Webhook signature verification failed")
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Unauthorized"}).encode())
            return
        
        # Parse payload
        try:
            payload = json.loads(request_body)
        except json.JSONDecodeError:
            logger.error("[v0] Failed to parse webhook payload JSON")
            self.send_response(400)
            self.end_headers()
            return
        
        # Process based on event type
        event_type = payload.get('event')
        data = payload.get('data', {})
        
        try:
            if event_type == 'charge.success':
                asyncio.run(self._handle_charge_success(data))
            
            # Always return 200 quickly to acknowledge receipt
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "received"}).encode())
            
        except Exception as e:
            logger.error(f"[v0] Webhook processing error: {e}")
            self.send_response(200)  # Still return 200 so Paystack doesn't retry
            self.end_headers()
    
    async def _handle_charge_success(self, data: dict):
        """Handle successful charge event (Task 1)"""
        
        reference = data.get('reference')
        status = data.get('status')
        metadata = data.get('metadata', {})
        
        if status != 'success' or not reference:
            logger.warning(f"[v0] Invalid charge success event: {data}")
            return
        
        payment_type = metadata.get('type')
        user_id = metadata.get('user_id')
        
        logger.info(f"[v0] Processing payment: {payment_type} for user {user_id}")
        
        try:
            if payment_type == 'group_pay_now':
                # Generic welcome-message "Pay Now" button (any group, any
                # admin-chosen purpose) — just mark it paid. The bot-side
                # "Verify" tap (handlers/welcome_pay.py) is what confirms to
                # the user and posts to the group; this is a backstop so the
                # payment_logs row is correct even if the user never taps
                # Verify.
                await db.mark_payment_paid(reference)
                logger.info(f"[v0] group_pay_now payment {reference} marked as paid")

            elif payment_type == 'bot_clone':
                # Mark clone payment as paid in database (Task 2)
                await db.mark_clone_payment_paid(reference)
                logger.info(f"[v0] Clone payment {reference} marked as paid")
                
            elif payment_type == 'ai_subscription':
                # Activate AI subscription for user (Task 3) — scoped to
                # whichever bot initiated this payment.
                if user_id:
                    clone_id = int(metadata.get('clone_id', 0) or 0)
                    await activate_subscription(user_id, months=1, clone_id=clone_id)
                    logger.info(f"[v0] Subscription activated for user {user_id} on clone_id={clone_id}")

            elif payment_type == 'botstore_premium':
                # Activate BotStore premium tier (unlimited listings) — scoped
                # to whichever bot (main = 0, or a specific clone) initiated
                # this payment, so it can't grant premium on a different bot.
                if user_id:
                    clone_id = int(metadata.get('clone_id', 0) or 0)
                    await db.set_premium_tier(int(user_id), clone_id=clone_id)
                    logger.info(f"[v0] BotStore premium activated for user {user_id} on clone_id={clone_id}")

            elif payment_type == 'clone_monetization':
                # Activate (or renew) a clone owner's monetization
                # subscription — unlocks connecting their own Paystack/Stripe
                # key and setting their own prices (handlers/clone_bot.py).
                clone_id = int(metadata.get('clone_id', 0) or 0)
                if clone_id:
                    from config import CLONE_MONETIZATION_DAYS
                    await db.activate_monetization_subscription(clone_id, days=CLONE_MONETIZATION_DAYS)
                    logger.info(f"[v0] Monetization activated for clone_id={clone_id}")

            elif payment_type == 'superbot_tier':
                # Activate a SuperBot premium tier (pro/elite)
                tier = metadata.get('tier')
                if user_id and tier:
                    from modules import superbot_adapter
                    await superbot_adapter.set_user_tier(int(user_id), tier)
                    logger.info(f"[v0] SuperBot tier '{tier}' activated for user {user_id}")
                    
        except Exception as e:
            logger.error(f"[v0] Error processing payment {reference}: {e}")
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        logger.debug(f"[v0] Webhook: {format % args}")


if __name__ == '__main__':
    from http.server import HTTPServer
    
    server = HTTPServer(('localhost', 3001), handler)
    print("[v0] Paystack webhook listening on http://localhost:3001")
    server.serve_forever()
