from datetime import datetime, timedelta
from typing import Dict, List
from config import RATE_LIMIT_SEARCHES, RATE_LIMIT_SUBMISSIONS

class RateLimiter:
    """Rate limiting for user actions"""
    
    def __init__(self):
        self.search_limits: Dict[int, List[datetime]] = {}
        self.submission_limits: Dict[int, List[datetime]] = {}
    
    def check_search_limit(self, user_id: int) -> bool:
        """Check if user exceeded search limit"""
        now = datetime.now()
        window = timedelta(hours=1)
        
        if user_id not in self.search_limits:
            self.search_limits[user_id] = []
        
        # Remove old entries outside the window
        self.search_limits[user_id] = [
            ts for ts in self.search_limits[user_id]
            if now - ts < window
        ]
        
        # Check if limit exceeded
        if len(self.search_limits[user_id]) >= RATE_LIMIT_SEARCHES:
            return False
        
        # Add new entry
        self.search_limits[user_id].append(now)
        return True
    
    def check_submission_limit(self, user_id: int) -> bool:
        """Check if user exceeded submission limit"""
        now = datetime.now()
        window = timedelta(hours=24)
        
        if user_id not in self.submission_limits:
            self.submission_limits[user_id] = []
        
        # Remove old entries outside the window
        self.submission_limits[user_id] = [
            ts for ts in self.submission_limits[user_id]
            if now - ts < window
        ]
        
        # Check if limit exceeded
        if len(self.submission_limits[user_id]) >= RATE_LIMIT_SUBMISSIONS:
            return False
        
        # Add new entry
        self.submission_limits[user_id].append(now)
        return True
    
    def get_search_remaining(self, user_id: int) -> int:
        """Get remaining searches for user"""
        now = datetime.now()
        window = timedelta(hours=1)
        
        if user_id not in self.search_limits:
            return RATE_LIMIT_SEARCHES
        
        valid_searches = [
            ts for ts in self.search_limits[user_id]
            if now - ts < window
        ]
        
        return max(0, RATE_LIMIT_SEARCHES - len(valid_searches))
    
    def get_submission_remaining(self, user_id: int) -> int:
        """Get remaining submissions for user"""
        now = datetime.now()
        window = timedelta(hours=24)
        
        if user_id not in self.submission_limits:
            return RATE_LIMIT_SUBMISSIONS
        
        valid_submissions = [
            ts for ts in self.submission_limits[user_id]
            if now - ts < window
        ]
        
        return max(0, RATE_LIMIT_SUBMISSIONS - len(valid_submissions))

# Global instance
rate_limiter = RateLimiter()
