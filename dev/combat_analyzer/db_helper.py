"""
Database Helper Module
Fetches character data from PostgreSQL database to enrich battle analysis.
"""
import os
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import psycopg2, provide helpful error if not installed
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


@dataclass
class CharacterInfo:
    """Complete character information from database."""
    # Basic info
    character_id: str
    name: str = ""
    description: str = ""
    
    # Character attributes
    status: str = ""
    collectable: bool = False
    boss: bool = False
    region: str = ""
    rarity: str = ""
    archetype: str = ""
    family: str = ""
    race: str = ""
    theme: str = ""
    original: bool = False
    battle_tier: str = ""
    
    # Stats
    attack: int = 0
    defense: int = 0
    health: int = 0
    speed: int = 0
    pct_to_avg: float = 0.0
    
    # Tags for matching
    archetype_tag: str = ""
    family_tag: str = ""
    race_tag: str = ""
    theme_tag: str = ""
    
    def get_summary(self) -> str:
        """Get a text summary for LLM context."""
        summary = f"{self.name}"
        if self.description:
            summary += f": {self.description}"
        
        attrs = []
        if self.rarity:
            attrs.append(f"{self.rarity} rarity")
        if self.archetype:
            attrs.append(f"{self.archetype} archetype")
        if self.region:
            attrs.append(f"from {self.region}")
        if self.theme:
            attrs.append(f"{self.theme} theme")
        if self.family:
            attrs.append(f"{self.family} family")
        
        if attrs:
            summary += f" ({', '.join(attrs)})"
        
        if self.attack or self.defense or self.health or self.speed:
            summary += f"\nBase Stats: ATK:{self.attack} DEF:{self.defense} HP:{self.health} SPD:{self.speed}"
            if self.pct_to_avg:
                summary += f" ({self.pct_to_avg:+.1%} vs avg)"
        
        return summary


class DatabaseHelper:
    """Helper class to fetch character data from database."""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database connection.
        
        Connection can be via:
        - DATABASE_URL environment variable (connection string)
        - Or passed directly as database_url parameter
        """
        if not HAS_PSYCOPG2:
            raise ImportError(
                "psycopg2 is required for database access. "
                "Install it with: pip install psycopg2-binary"
            )
        
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found. Set it in .env file or pass directly."
            )
        
        self._connection = None
        self._character_cache: Dict[str, CharacterInfo] = {}
    
    def connect(self):
        """Establish database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(self.database_url)
        return self._connection
    
    def close(self):
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
    
    def _normalize_character_id(self, char_id: str) -> str:
        """Normalize character ID for matching."""
        # Remove common suffixes like _l, _r (team indicators)
        normalized = char_id.lower().strip()
        if normalized.endswith('_l') or normalized.endswith('_r'):
            normalized = normalized[:-2]
        return normalized
    
    def get_character(self, character_id: str) -> Optional[CharacterInfo]:
        """
        Fetch character info by ID or name.
        
        Searches in order:
        1. Exact match on character column
        2. Match on character_id in names_descriptions
        3. Fuzzy match on name
        """
        normalized_id = self._normalize_character_id(character_id)
        
        # Check cache first
        if normalized_id in self._character_cache:
            return self._character_cache[normalized_id]
        
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Query 1: Try exact match on characters table
            cursor.execute("""
                SELECT c.*, 
                       nd.name, nd.description,
                       sa.attack, sa.defense, sa.health, sa.speed, sa.pct_to_avg
                FROM characters c
                LEFT JOIN names_descriptions nd ON c.character = nd.character_id
                LEFT JOIN stats_analysis sa ON nd.name = sa.character_name
                WHERE LOWER(c.character) = %s
                   OR LOWER(c.character) LIKE %s
                   OR LOWER(c.normal_name) = %s
                LIMIT 1
            """, (normalized_id, f"%{normalized_id}%", normalized_id))
            
            row = cursor.fetchone()
            
            # Query 2: If not found, try names_descriptions
            if not row:
                cursor.execute("""
                    SELECT c.*, 
                           nd.name, nd.description,
                           sa.attack, sa.defense, sa.health, sa.speed, sa.pct_to_avg
                    FROM names_descriptions nd
                    LEFT JOIN characters c ON c.character = nd.character_id
                    LEFT JOIN stats_analysis sa ON nd.name = sa.character_name
                    WHERE LOWER(nd.character_id) LIKE %s
                       OR LOWER(nd.name) LIKE %s
                    LIMIT 1
                """, (f"%{normalized_id}%", f"%{normalized_id.replace('_', ' ')}%"))
                
                row = cursor.fetchone()
            
            if row:
                char_info = CharacterInfo(
                    character_id=row.get('character', normalized_id),
                    name=row.get('name', '') or row.get('normal_name', '') or normalized_id,
                    description=row.get('description', '') or '',
                    status=row.get('status', '') or '',
                    collectable=row.get('collectable', False) or False,
                    boss=row.get('boss', False) or False,
                    region=row.get('region', '') or '',
                    rarity=row.get('rarity', '') or '',
                    archetype=row.get('archetype', '') or '',
                    family=row.get('family', '') or '',
                    race=row.get('race', '') or '',
                    theme=row.get('theme', '') or '',
                    original=row.get('original', False) or False,
                    battle_tier=row.get('battle_tier', '') or '',
                    attack=row.get('attack', 0) or 0,
                    defense=row.get('defense', 0) or 0,
                    health=row.get('health', 0) or 0,
                    speed=row.get('speed', 0) or 0,
                    pct_to_avg=float(row.get('pct_to_avg', 0) or 0),
                    archetype_tag=row.get('archetype_tag', '') or '',
                    family_tag=row.get('family_tag', '') or '',
                    race_tag=row.get('race_tag', '') or '',
                    theme_tag=row.get('theme_tag', '') or ''
                )
                
                # Cache the result
                self._character_cache[normalized_id] = char_info
                return char_info
            
            return None
            
        finally:
            cursor.close()
    
    def get_characters_batch(self, character_ids: List[str]) -> Dict[str, CharacterInfo]:
        """Fetch multiple characters at once."""
        results = {}
        for char_id in character_ids:
            char_info = self.get_character(char_id)
            if char_info:
                results[self._normalize_character_id(char_id)] = char_info
        return results
    
    def get_character_context_for_battle(self, character_names: List[str]) -> str:
        """
        Get formatted context string for all characters in a battle.
        This is meant to be included in the LLM prompt.
        """
        context_parts = []
        
        for name in character_names:
            char_info = self.get_character(name)
            if char_info:
                context_parts.append(char_info.get_summary())
            else:
                context_parts.append(f"{name}: No database info available")
        
        if context_parts:
            return "## Character Database Info\n" + "\n\n".join(context_parts)
        return ""
    
    def search_characters(self, query: str, limit: int = 10) -> List[CharacterInfo]:
        """Search for characters by name or attributes."""
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT c.*, 
                       nd.name, nd.description,
                       sa.attack, sa.defense, sa.health, sa.speed, sa.pct_to_avg
                FROM characters c
                LEFT JOIN names_descriptions nd ON c.character = nd.character_id
                LEFT JOIN stats_analysis sa ON nd.name = sa.character_name
                WHERE LOWER(c.character) LIKE %s
                   OR LOWER(c.normal_name) LIKE %s
                   OR LOWER(nd.name) LIKE %s
                   OR LOWER(c.archetype) LIKE %s
                   OR LOWER(c.theme) LIKE %s
                LIMIT %s
            """, (f"%{query.lower()}%",) * 5 + (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append(CharacterInfo(
                    character_id=row.get('character', ''),
                    name=row.get('name', '') or row.get('normal_name', ''),
                    description=row.get('description', '') or '',
                    status=row.get('status', '') or '',
                    collectable=row.get('collectable', False) or False,
                    boss=row.get('boss', False) or False,
                    region=row.get('region', '') or '',
                    rarity=row.get('rarity', '') or '',
                    archetype=row.get('archetype', '') or '',
                    family=row.get('family', '') or '',
                    race=row.get('race', '') or '',
                    theme=row.get('theme', '') or '',
                    original=row.get('original', False) or False,
                    battle_tier=row.get('battle_tier', '') or '',
                    attack=row.get('attack', 0) or 0,
                    defense=row.get('defense', 0) or 0,
                    health=row.get('health', 0) or 0,
                    speed=row.get('speed', 0) or 0,
                    pct_to_avg=float(row.get('pct_to_avg', 0) or 0)
                ))
            
            return results
            
        finally:
            cursor.close()


# Singleton instance for easy access
_db_helper: Optional[DatabaseHelper] = None


def get_db_helper() -> Optional[DatabaseHelper]:
    """Get or create the database helper singleton."""
    global _db_helper
    
    if not HAS_PSYCOPG2:
        return None
    
    if _db_helper is None:
        try:
            _db_helper = DatabaseHelper()
            # Test connection
            _db_helper.connect()
        except Exception as e:
            print(f"Warning: Could not connect to database: {e}")
            return None
    
    return _db_helper


def get_character_info(character_id: str) -> Optional[CharacterInfo]:
    """Convenience function to get character info."""
    db = get_db_helper()
    if db:
        return db.get_character(character_id)
    return None


def get_battle_character_context(character_names: List[str]) -> str:
    """Convenience function to get context for battle characters."""
    db = get_db_helper()
    if db:
        return db.get_character_context_for_battle(character_names)
    return ""
