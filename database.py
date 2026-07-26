import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import sqlite3
import aiosqlite

from config import DATABASE_URL, USE_POSTGRESQL

class Database:
    """Database handler for SQLite and PostgreSQL"""
    
    def __init__(self):
        self.db_path = DATABASE_URL.replace("sqlite:///", "") if not USE_POSTGRESQL else None
        self.connection = None
    
    async def init(self):
        """Initialize database tables"""
        if USE_POSTGRESQL:
            # For PostgreSQL, would use asyncpg here
            # For now, we'll use SQLite for local testing
            pass
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
    
    async def _create_tables(self, db):
        """Create all necessary tables"""
        
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tier TEXT DEFAULT 'free',
                submissions_count INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                stripe_key TEXT
            )
        """)
        
        # Submissions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                anime_name TEXT NOT NULL,
                episodes INTEGER,
                genres TEXT,
                synopsis TEXT,
                image_url TEXT,
                status TEXT DEFAULT 'pending',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_date TIMESTAMP,
                rejection_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Cloned bots table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cloned_bots (
                clone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                bot_name TEXT NOT NULL,
                bot_token TEXT UNIQUE NOT NULL,
                webhook_url TEXT,
                custom_data TEXT,
                status TEXT DEFAULT 'active',
                payment_id TEXT,
                payment_status TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        """)
        
        # Anime entries table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime_entries (
                anime_id INTEGER PRIMARY KEY AUTOINCREMENT,
                anilist_id INTEGER UNIQUE,
                mal_id INTEGER UNIQUE,
                title TEXT NOT NULL,
                episodes INTEGER,
                genres TEXT,
                rating REAL,
                status TEXT,
                synopsis TEXT,
                image_url TEXT,
                source_api TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                category_name TEXT NOT NULL,
                emoji TEXT,
                anime_ids TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        """)
        
        # Payment logs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_logs (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                paystack_reference TEXT UNIQUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Commission tracking table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS commission_tracking (
                commission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cloned_bot_id INTEGER NOT NULL,
                payment_amount INTEGER NOT NULL,
                main_commission INTEGER NOT NULL,
                owner_amount INTEGER NOT NULL,
                stripe_key_id TEXT,
                payment_intent_id TEXT UNIQUE,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cloned_bot_id) REFERENCES cloned_bots(clone_id)
            )
        """)
        
        # Subscription payments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscription_payments (
                subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_amount INTEGER NOT NULL,
                subscription_month TEXT NOT NULL,
                payment_method TEXT,
                payment_reference TEXT UNIQUE,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()
    
    async def add_user(self, user_id: int, username: str, first_name: str, is_admin: bool = False):
        """Add or update a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, is_admin)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, 1 if is_admin else 0))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user info"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "username": row[1],
                        "first_name": row[2],
                        "joined_date": row[3],
                        "tier": row[4],
                        "submissions_count": row[5],
                        "is_admin": bool(row[6])
                    }
        return None
    
    async def add_submission(self, user_id: int, anime_name: str, episodes: int, genres: str, synopsis: str, image_url: str):
        """Add a new submission"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO submissions (user_id, anime_name, episodes, genres, synopsis, image_url, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, anime_name, episodes, genres, synopsis, image_url))
            await db.commit()
            return cursor.lastrowid
    
    async def get_pending_submissions(self) -> List[Dict]:
        """Get all pending submissions"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM submissions WHERE status = 'pending' ORDER BY created_date DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "submission_id": row[0],
                    "user_id": row[1],
                    "anime_name": row[2],
                    "episodes": row[3],
                    "genres": row[4],
                    "synopsis": row[5],
                    "image_url": row[6],
                    "status": row[7],
                    "created_date": row[8]
                } for row in rows]
    
    async def approve_submission(self, submission_id: int):
        """Approve a submission"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE submissions SET status = 'approved', approved_date = CURRENT_TIMESTAMP 
                WHERE submission_id = ?
            """, (submission_id,))
            await db.commit()
    
    async def reject_submission(self, submission_id: int, reason: str):
        """Reject a submission"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE submissions SET status = 'rejected', rejection_reason = ?
                WHERE submission_id = ?
            """, (reason, submission_id))
            await db.commit()
    
    async def add_cloned_bot(self, owner_id: int, bot_name: str, bot_token: str, webhook_url: str, custom_data: Dict):
        """Add a cloned bot"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO cloned_bots (owner_id, bot_name, bot_token, webhook_url, custom_data)
                VALUES (?, ?, ?, ?, ?)
            """, (owner_id, bot_name, bot_token, webhook_url, json.dumps(custom_data)))
            await db.commit()
            return cursor.lastrowid
    
    async def get_user_clones(self, user_id: int) -> List[Dict]:
        """Get all cloned bots for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM cloned_bots WHERE owner_id = ? AND status = 'active'
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "clone_id": row[0],
                    "owner_id": row[1],
                    "bot_name": row[2],
                    "bot_token": row[3],
                    "webhook_url": row[4],
                    "custom_data": json.loads(row[5]) if row[5] else {},
                    "created_date": row[8]
                } for row in rows]
    
    async def add_anime(self, title: str, episodes: int, genres: str, rating: float, status: str, synopsis: str, image_url: str, anilist_id: Optional[int] = None, mal_id: Optional[int] = None):
        """Add anime entry"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO anime_entries (anilist_id, mal_id, title, episodes, genres, rating, status, synopsis, image_url, source_api)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'mixed')
            """, (anilist_id, mal_id, title, episodes, genres, rating, status, synopsis, image_url))
            await db.commit()
            return cursor.lastrowid
    
    async def search_anime(self, query: str, limit: int = 5) -> List[Dict]:
        """Search anime by title"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM anime_entries WHERE title LIKE ? LIMIT ?
            """, (f"%{query}%", limit)) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "anime_id": row[0],
                    "title": row[3],
                    "episodes": row[4],
                    "genres": row[5],
                    "rating": row[6],
                    "status": row[7],
                    "synopsis": row[8],
                    "image_url": row[9]
                } for row in rows]

# Global database instance
db = Database()
