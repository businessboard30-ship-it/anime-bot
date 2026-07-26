import re
from typing import Tuple

class InputValidator:
    """Validate user inputs"""
    
    @staticmethod
    def validate_anime_name(name: str) -> Tuple[bool, str]:
        """Validate anime name"""
        if not name or len(name.strip()) == 0:
            return False, "Anime name cannot be empty"
        
        if len(name) > 200:
            return False, "Anime name too long (max 200 characters)"
        
        return True, "valid"
    
    @staticmethod
    def validate_episodes(episodes_str: str) -> Tuple[bool, int]:
        """Validate episode count"""
        if episodes_str.lower() == "unknown" or episodes_str.lower() == "?":
            return True, 0
        
        try:
            episodes = int(episodes_str)
            if episodes < 0 or episodes > 500:
                return False, -1
            return True, episodes
        except ValueError:
            return False, -1
    
    @staticmethod
    def validate_genres(genres_str: str) -> Tuple[bool, str]:
        """Validate genres input"""
        if not genres_str or len(genres_str.strip()) == 0:
            return True, "Not specified"
        
        genres = [g.strip() for g in genres_str.split(",") if g.strip()]
        
        if len(genres) > 10:
            return False, ""
        
        return True, ", ".join(genres[:10])
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Validate webhook URL"""
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        
        if not url or len(url.strip()) == 0:
            return True, ""  # Optional field
        
        if re.match(url_pattern, url):
            return True, url
        
        return False, "Invalid URL format"
    
    @staticmethod
    def validate_bot_name(name: str) -> Tuple[bool, str]:
        """Validate clone bot name"""
        if not name or len(name.strip()) == 0:
            return False, "Bot name cannot be empty"
        
        if len(name) > 50:
            return False, "Bot name too long (max 50 characters)"
        
        # Only alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False, "Bot name can only contain letters, numbers, underscore, hyphen"
        
        return True, name
    
    @staticmethod
    def validate_synopsis(synopsis: str) -> Tuple[bool, str]:
        """Validate anime synopsis/description"""
        if not synopsis or len(synopsis.strip()) == 0:
            return True, "No description provided"
        
        if len(synopsis) > 1000:
            return False, "Synopsis too long (max 1000 characters)"
        
        return True, synopsis.strip()
