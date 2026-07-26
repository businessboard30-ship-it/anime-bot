import aiohttp
import json
from typing import List, Dict, Optional
from datetime import datetime
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

class GroqService:
    """AI service for anime recommendations and summaries using Groq API"""
    
    def __init__(self):
        self.model = "mixtral-8x7b-32768"
        self.cache = {}
        self.cache_ttl = 86400  # 24 hours
    
    async def get_anime_recommendation(self, user_preferences: str, anime_watched: List[str]) -> str:
        """Get AI-powered anime recommendation based on user preferences"""
        if not GROQ_API_KEY:
            return "Yo, AI recommendations are currently down. Try again later! 🤖"
        
        watched_list = ", ".join(anime_watched[-5:]) if anime_watched else "No anime watched yet"
        
        prompt = f"""You are a cool, Gen Z anime expert assistant. Recommend anime based on these preferences:
        
User Preferences: {user_preferences}
Recently Watched: {watched_list}

Give a SHORT, CASUAL recommendation (2-3 sentences MAX). Use Gen Z slang, be chill about it.
Format: "[Anime Name] - why it slaps for you 🎬"

Keep it under 150 characters total."""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 100,
                }
                
                async with session.post(GROQ_ENDPOINT, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        return f"Recommendation failed. Try again! ({resp.status})"
        except Exception as e:
            return f"Oops! AI is sleeping rn. Error: {str(e)[:30]}"
    
    async def get_anime_summary(self, anime_title: str, anime_description: str) -> str:
        """Generate Gen Z-style summary of an anime"""
        if not GROQ_API_KEY:
            return "Summaries are offline atm! 😴"
        
        prompt = f"""You are a Gen Z anime expert. Summarize this anime in the most casual, trendy way:

Anime: {anime_title}
Description: {anime_description[:500]}

Write a SUPER SHORT summary (1 sentence, max 100 chars) using Gen Z slang.
Make it sound like you're texting a friend about it.
Use relevant emojis.

Example: "bro this anime is literally insane, the action hits different fr fr 🔥"

Just give the summary, nothing else."""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 80,
                }
                
                async with session.post(GROQ_ENDPOINT, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        return f"Can't summarize rn! Try later 😅"
        except Exception as e:
            return f"Summary failed lol. {str(e)[:20]}"
    
    def _get_cache_key(self, key: str) -> Optional[str]:
        """Get value from cache if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now().timestamp() - entry["timestamp"] < self.cache_ttl:
                return entry["value"]
        return None
    
    def _set_cache(self, key: str, value: str):
        """Store value in cache"""
        self.cache[key] = {
            "value": value,
            "timestamp": datetime.now().timestamp()
        }


# Global instance
groq_service = GroqService()
