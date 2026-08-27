"""
AI Features Module — Conversational AI Chat & Image Generation
Uses Groq API for chat (anime questions, general chat)
Uses Fal AI or Replicate for image generation
Gated behind premium tier system (superbot_adapter.get_user_tier)
"""

import aiohttp
import logging
from typing import Optional, List, Dict
from datetime import datetime
from database import get_pool

logger = logging.getLogger(__name__)

# AI_GATEWAY_API_KEY or provider keys from env
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ═══════════════════════════════════════════════════════════════════════════
# AI CHAT with conversation history
# ═══════════════════════════════════════════════════════════════════════════

AI_CHAT_MODEL = "openai/gpt-oss-120b"  # Groq's current recommended general-purpose model
SYSTEM_PROMPT_ANIME = (
    "You are an anime expert and helpful assistant. Provide friendly, concise responses about anime, manga, characters, and recommendations. "
    "Keep answers under 500 characters when possible. Be conversational and engaging."
)
SYSTEM_PROMPT_GENERAL = (
    "You are a helpful, friendly assistant. Provide concise, accurate responses to questions. "
    "Keep answers under 500 characters when possible."
)

# User AI usage caps (per tier)
AI_USAGE_CAPS = {
    "basic": {"daily_messages": 10, "daily_images": 1},
    "pro": {"daily_messages": 100, "daily_images": 10},
    "elite": {"daily_messages": 1000, "daily_images": 100},
    "founder": {"daily_messages": 10000, "daily_images": 10000},
}


async def get_user_ai_usage(user_id: int, usage_type: str = "messages") -> int:
    """Get today's AI usage count for user (messages or images)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            today = datetime.now().date()
            
            table = "ai_chat_usage" if usage_type == "messages" else "ai_image_usage"
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {table} WHERE user_id = $1 AND DATE(created_at) = $2",
                user_id, today
            )
        return count or 0
    except Exception as e:
        logger.error(f"[v0] Error getting AI usage: {e}")
        return 0


async def log_ai_usage(user_id: int, usage_type: str = "messages", prompt_text: str = "", response_text: str = "") -> bool:
    """Log AI feature usage for rate limiting. For chat messages, also stores
    the assistant's reply (response_text) so it can be replayed as real
    conversation history next time — see get_ai_conversation_history."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if usage_type == "messages":
                await conn.execute(
                    "INSERT INTO ai_chat_usage (user_id, prompt, response, created_at) VALUES ($1, $2, $3, NOW())",
                    user_id, prompt_text[:500], response_text[:2000]
                )
            else:
                await conn.execute(
                    "INSERT INTO ai_image_usage (user_id, prompt, created_at) VALUES ($1, $2, NOW())",
                    user_id, prompt_text[:500]
                )
        return True
    except Exception as e:
        logger.error(f"[v0] Error logging AI usage: {e}")
        return False


async def get_ai_conversation_history(user_id: int, limit: int = 10) -> List[Dict]:
    """Get recent conversation turns (prompt + the assistant's actual reply)
    for context, oldest first so callers can replay them in order."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT prompt, response, created_at FROM ai_chat_usage "
                "WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                user_id, limit
            )
            return [dict(row) for row in reversed(rows)]
    except Exception as e:
        logger.error(f"[v0] Error fetching conversation history: {e}")
        return []


async def ai_chat(user_id: int, message: str, is_anime_question: bool = False) -> Optional[str]:
    """
    Send message to Groq API and get response.
    Returns response text on success. On failure, returns None (caller shows
    a generic "AI service error" to the user) but ALSO stashes the real
    error string on `ai_chat.last_error` so an admin-facing surface (see
    handlers/ai_handler.py) can show the actual cause — missing key, bad
    model name, Groq outage, rate limit, etc. — instead of just "None".
    """
    ai_chat.last_error = None
    try:
        if not GROQ_API_KEY:
            ai_chat.last_error = "GROQ_API_KEY is not set in the environment."
            return "⚠️ AI service not configured. Admin needs to set GROQ_API_KEY."
        
        # Get conversation history for context (oldest first)
        history = await get_ai_conversation_history(user_id, limit=5)
        
        # Build conversation with context
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_ANIME if is_anime_question else SYSTEM_PROMPT_GENERAL}
        ]
        
        # Replay the last few turns as real alternating user/assistant
        # messages, so the model actually remembers what it said, not just
        # what the user asked before.
        for hist in history[-3:]:
            if hist.get('prompt'):
                messages.append({"role": "user", "content": hist['prompt'][:200]})
            if hist.get('response'):
                messages.append({"role": "assistant", "content": hist['response'][:400]})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Groq API
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": AI_CHAT_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_completion_tokens": 600,
                "reasoning_effort": "low",
                "top_p": 1.0
            }
            
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    if response_text:
                        # Log usage, including the reply itself so next
                        # turn's history replay has something to remember.
                        await log_ai_usage(user_id, "messages", message, response_text)
                        return response_text
                else:
                    error = await resp.text()
                    ai_chat.last_error = f"Groq API HTTP {resp.status}: {error[:300]}"
                    logger.error(f"[v0] Groq API error: {error}")
        
        return None
    
    except Exception as e:
        ai_chat.last_error = f"{type(e).__name__}: {e}"
        logger.error(f"[v0] Error in ai_chat: {e}")
        return None


ai_chat.last_error = None  # set fresh on each call; see docstring above


# ═══════════════════════════════════════════════════════════════════════════
# AI IMAGE GENERATION
# ═══════════════════════════════════════════════════════════════════════════

async def generate_image(user_id: int, prompt: str, style: str = "anime") -> Optional[Dict]:
    """
    Generate an image from prompt using Fal AI or OpenAI DALL-E.
    Returns dict with: url, prompt, model, generation_time_ms, style
    """
    try:
        if not FAL_API_KEY and not OPENAI_API_KEY:
            return {"error": "Image generation service not configured."}
        
        # Clean and validate prompt
        prompt = prompt.strip()[:500]
        if not prompt or len(prompt) < 5:
            return {"error": "Prompt must be at least 5 characters."}
        
        # Add style prefix
        if style == "anime":
            full_prompt = f"anime style, {prompt}"
        elif style == "realistic":
            full_prompt = f"realistic, {prompt}"
        elif style == "3d":
            full_prompt = f"3d render, {prompt}"
        else:
            full_prompt = prompt
        
        # Try Fal AI first
        if FAL_API_KEY:
            result = await _generate_image_fal(full_prompt)
            if result:
                await log_ai_usage(user_id, "images", prompt)
                return result
        
        # Fallback to OpenAI DALL-E
        if OPENAI_API_KEY:
            result = await _generate_image_openai(full_prompt)
            if result:
                await log_ai_usage(user_id, "images", prompt)
                return result
        
        return {"error": "Image generation failed. Try again later."}
    
    except Exception as e:
        logger.error(f"[v0] Error in generate_image: {e}")
        return {"error": str(e)[:100]}


async def _generate_image_fal(prompt: str) -> Optional[Dict]:
    """Generate image using Fal AI (fast, anime-friendly)."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Key {FAL_API_KEY}"}
            
            # Use Fal's FLUX model for anime-style images
            payload = {
                "prompt": prompt,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "image_size": "square"
            }
            
            async with session.post(
                "https://fal.run/fal-ai/flux-pro",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get('images') and len(data['images']) > 0:
                        image_url = data['images'][0].get('url')
                        if image_url:
                            return {
                                "url": image_url,
                                "prompt": prompt,
                                "model": "fal-ai",
                                "generation_time_ms": 0,
                                "style": "anime"
                            }
        
        return None
    
    except Exception as e:
        logger.error(f"[v0] Fal image generation error: {e}")
        return None


async def _generate_image_openai(prompt: str) -> Optional[Dict]:
    """Generate image using OpenAI DALL-E."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": "512x512",
                "model": "dall-e-3"
            }
            
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get('data') and len(data['data']) > 0:
                        image_url = data['data'][0].get('url')
                        if image_url:
                            return {
                                "url": image_url,
                                "prompt": prompt,
                                "model": "dall-e-3",
                                "generation_time_ms": 0,
                                "style": "general"
                            }
        
        return None
    
    except Exception as e:
        logger.error(f"[v0] OpenAI image generation error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# AI USAGE CHECKS
# ═══════════════════════════════════════════════════════════════════════════

async def check_ai_usage_limit(user_id: int, tier: str, usage_type: str = "messages") -> tuple[bool, str]:
    """
    Check if user has hit daily AI usage limit for their tier.
    Returns (is_allowed: bool, message: str)
    """
    try:
        if tier not in AI_USAGE_CAPS:
            tier = "basic"
        
        cap = AI_USAGE_CAPS[tier].get("daily_messages" if usage_type == "messages" else "daily_images")
        usage = await get_user_ai_usage(user_id, usage_type)
        
        if usage >= cap:
            cap_name = "messages" if usage_type == "messages" else "image"
            return (False, f"Daily {cap_name} limit reached ({usage}/{cap}). Upgrade your tier or try tomorrow.")
        
        # Warn if near limit
        if usage >= cap * 0.8:
            cap_name = "messages" if usage_type == "messages" else "images"
            return (True, f"⚠️ You're near your daily {cap_name} limit ({usage}/{cap})")
        
        return (True, "")
    
    except Exception as e:
        logger.error(f"[v0] Error checking AI usage: {e}")
        return (True, "")  # Allow by default if error
