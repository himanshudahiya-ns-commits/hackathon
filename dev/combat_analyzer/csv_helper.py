"""
CSV Helper Module
Loads character and skill data from CSV files to enrich battle analysis.
"""
import os
import csv
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from pathlib import Path


@dataclass
class SkillInfo:
    """Information about a skill."""
    skill_id: str
    skill_name: str
    skill_level: int = 0
    skill_type: str = ""  # Active, Passive, etc.
    cost: str = ""
    description: str = ""
    owner_character: str = ""
    is_max_level: bool = False


@dataclass 
class CharacterCSVInfo:
    """Character information from CSV files."""
    character_id: str
    display_name: str = ""
    
    # Attributes
    theme: str = ""
    theme2: str = ""
    rarity: str = ""
    archetype: str = ""
    race: str = ""
    family: str = ""
    region: str = ""
    house: str = ""
    
    # Base stats
    base_attack: int = 0
    base_defense: int = 0
    base_health: int = 0
    base_speed: int = 0
    
    # Relative stats (% compared to average)
    rel_attack: str = ""
    rel_defense: str = ""
    rel_health: str = ""
    rel_speed: str = ""
    
    # Max stats
    max_attack: int = 0
    max_defense: int = 0
    max_health: int = 0
    max_speed: int = 0
    total_power: int = 0
    
    # Skills
    skills: List[SkillInfo] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Get a text summary for LLM context."""
        parts = [f"**{self.display_name}**"]
        
        attrs = []
        if self.rarity:
            attrs.append(self.rarity)
        if self.archetype:
            attrs.append(self.archetype)
        if self.region:
            attrs.append(f"from {self.region}")
        if self.theme:
            attrs.append(f"{self.theme} theme")
        
        if attrs:
            parts.append(f"({', '.join(attrs)})")
        
        if self.base_attack:
            stats = f"Base Stats: ATK:{self.base_attack} DEF:{self.base_defense} HP:{self.base_health} SPD:{self.base_speed}"
            if self.rel_attack:
                stats += f" | Relative: ATK:{self.rel_attack} DEF:{self.rel_defense} HP:{self.rel_health} SPD:{self.rel_speed}"
            parts.append(stats)
        
        return " ".join(parts)


class CSVDataLoader:
    """Loads and caches data from CSV files."""
    
    def __init__(self, csv_dir: str = None):
        """
        Initialize CSV loader.
        
        Args:
            csv_dir: Directory containing CSV files. Defaults to sourse folder.
        """
        if csv_dir:
            self.csv_dir = Path(csv_dir)
        else:
            # Default to sourse folder relative to this file
            self.csv_dir = Path(__file__).parent.parent.parent / "sourse"
        
        self._characters: Dict[str, CharacterCSVInfo] = {}
        self._skills: Dict[str, SkillInfo] = {}
        self._skills_by_character: Dict[str, List[SkillInfo]] = {}
        self._loaded = False
    
    def _clean_description(self, desc: str) -> str:
        """Clean up skill description by removing markup tags."""
        if not desc:
            return ""
        # Remove tags like <OFF>, <DEF>, <DB>, <SP>, <>
        cleaned = re.sub(r'<[A-Z]*>', '', desc)
        cleaned = re.sub(r'<>', '', cleaned)
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def _parse_int(self, value: str) -> int:
        """Safely parse integer from string."""
        if not value:
            return 0
        try:
            # Remove commas and parse
            return int(value.replace(',', '').strip())
        except (ValueError, AttributeError):
            return 0
    
    def load_database_csv(self):
        """Load the DATABASE.csv file with character and skill info."""
        csv_path = self.csv_dir / "[LT] Toon Kits - _DATABASE.csv"
        
        if not csv_path.exists():
            print(f"Warning: DATABASE CSV not found at {csv_path}")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip the header row with column groups
            next(f)
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    char_id = row.get('Character ID', '').strip()
                    if not char_id:
                        continue
                    
                    # Create or update character
                    if char_id not in self._characters:
                        self._characters[char_id] = CharacterCSVInfo(
                            character_id=char_id,
                            display_name=row.get('Ref. Character', '').strip(),
                            theme=row.get('Theme', '').strip(),
                            theme2=row.get('Theme 2', '').strip(),
                            rarity=row.get('Rarity', '').strip(),
                            archetype=row.get('Archetype', '').strip(),
                            race=row.get('Race', '').strip(),
                            family=row.get('Family', '').strip(),
                            region=row.get('Region', '').strip(),
                            house=row.get('House', '').strip(),
                            base_attack=self._parse_int(row.get('Attack', '')),
                            base_defense=self._parse_int(row.get('Defense', '')),
                            base_health=self._parse_int(row.get('Health', '')),
                            base_speed=self._parse_int(row.get('Speed', '')),
                            total_power=self._parse_int(row.get('Total Power', ''))
                        )
                        
                        # Handle relative stats (they appear after base stats with same names)
                        # The CSV has duplicate column names, so we need to handle this
                    
                    # Create skill
                    skill_id = row.get('Skill ID', '').strip()
                    if skill_id:
                        skill_level = row.get('Skill Level', '').strip()
                        skill = SkillInfo(
                            skill_id=skill_id,
                            skill_name=row.get('Skill Name', '').strip(),
                            skill_level=self._parse_int(skill_level) if skill_level else 0,
                            skill_type=row.get('Type / Cost', '').strip(),
                            description=row.get('Description', '').strip(),
                            owner_character=row.get('Ref. Character', '').strip(),
                            is_max_level=row.get('Is Max TU', '').strip().upper() == 'TRUE'
                        )
                        
                        self._skills[skill_id] = skill
                        
                        # Add to character's skill list
                        if char_id not in self._skills_by_character:
                            self._skills_by_character[char_id] = []
                        self._skills_by_character[char_id].append(skill)
                        
                except Exception as e:
                    # Skip problematic rows
                    continue
    
    def load_skills_summary_csv(self):
        """Load the SKILLS SUMMARY.csv file with cleaner skill descriptions."""
        csv_path = self.csv_dir / "[LT] Toon Kits - _SKILLS SUMMARY.csv"
        
        if not csv_path.exists():
            print(f"Warning: SKILLS SUMMARY CSV not found at {csv_path}")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            for row in reader:
                if len(row) < 4:
                    continue
                
                try:
                    character_name = row[0].strip()
                    skill_id = row[1].strip()
                    skill_name = row[2].strip()
                    description = self._clean_description(row[3]) if len(row) > 3 else ""
                    skill_type = row[4].strip() if len(row) > 4 else ""
                    cost = row[5].strip() if len(row) > 5 else ""
                    
                    # Update existing skill or create new one
                    if skill_id in self._skills:
                        # Update with cleaner description
                        self._skills[skill_id].description = description
                    else:
                        skill = SkillInfo(
                            skill_id=skill_id,
                            skill_name=skill_name,
                            skill_type=skill_type,
                            cost=cost,
                            description=description,
                            owner_character=character_name
                        )
                        self._skills[skill_id] = skill
                        
                except Exception as e:
                    continue
    
    def load_all(self):
        """Load all CSV data."""
        if self._loaded:
            return
        
        self.load_database_csv()
        self.load_skills_summary_csv()
        self._loaded = True
    
    def get_character(self, character_id: str) -> Optional[CharacterCSVInfo]:
        """
        Get character info by ID.
        
        Tries multiple matching strategies:
        1. Exact match on character_id
        2. Partial match (e.g., 'bugs_bunny' matches 'bugs_bunny_pirate')
        3. Match on display name
        """
        self.load_all()
        
        # Normalize the ID
        normalized = character_id.lower().strip()
        if normalized.endswith('_l') or normalized.endswith('_r'):
            normalized = normalized[:-2]
        
        # Try exact match
        if normalized in self._characters:
            return self._characters[normalized]
        
        # Try partial match on character_id
        for char_id, char_info in self._characters.items():
            if normalized in char_id.lower() or char_id.lower() in normalized:
                return char_info
        
        # Try match on display name
        for char_id, char_info in self._characters.items():
            display_lower = char_info.display_name.lower().replace(' ', '_')
            if normalized in display_lower or display_lower in normalized:
                return char_info
        
        return None
    
    def get_skill(self, skill_id: str) -> Optional[SkillInfo]:
        """Get skill info by ID."""
        self.load_all()
        
        # Try exact match
        if skill_id in self._skills:
            return self._skills[skill_id]
        
        # Try without level suffix (e.g., skill_xyz_1 -> skill_xyz)
        base_skill = re.sub(r'_\d+$', '', skill_id)
        for sid, skill in self._skills.items():
            if sid.startswith(base_skill):
                return skill
        
        return None
    
    def get_character_skills(self, character_id: str) -> List[SkillInfo]:
        """Get all skills for a character."""
        self.load_all()
        
        # Normalize
        normalized = character_id.lower().strip()
        if normalized.endswith('_l') or normalized.endswith('_r'):
            normalized = normalized[:-2]
        
        # Try direct lookup
        if normalized in self._skills_by_character:
            return self._skills_by_character[normalized]
        
        # Try partial match
        for char_id, skills in self._skills_by_character.items():
            if normalized in char_id.lower() or char_id.lower() in normalized:
                return skills
        
        return []
    
    def get_character_info_dict(self, character_id: str) -> dict:
        """Get character info as a dictionary for LLM context."""
        char = self.get_character(character_id)
        if not char:
            return {}
        
        skills = self.get_character_skills(character_id)
        
        # Get max level skills only for cleaner output
        max_skills = [s for s in skills if s.is_max_level] or skills[:4]
        
        return {
            "display_name": char.display_name,
            "rarity": char.rarity,
            "archetype": char.archetype,
            "theme": char.theme,
            "region": char.region,
            "family": char.family,
            "race": char.race,
            "base_stats": {
                "attack": char.base_attack,
                "defense": char.base_defense,
                "health": char.base_health,
                "speed": char.base_speed
            },
            "relative_stats": {
                "attack": char.rel_attack,
                "defense": char.rel_defense,
                "health": char.rel_health,
                "speed": char.rel_speed
            },
            "total_power": char.total_power,
            "skills": [
                {
                    "name": s.skill_name,
                    "type": s.skill_type,
                    "description": s.description[:200] + "..." if len(s.description) > 200 else s.description
                }
                for s in max_skills[:4]  # Limit to 4 skills to keep context manageable
            ]
        }
    
    def get_skill_info_dict(self, skill_id: str) -> dict:
        """Get skill info as a dictionary."""
        skill = self.get_skill(skill_id)
        if not skill:
            return {}
        
        return {
            "skill_id": skill.skill_id,
            "name": skill.skill_name,
            "type": skill.skill_type,
            "description": skill.description,
            "owner": skill.owner_character
        }


# Singleton instance
_csv_loader: Optional[CSVDataLoader] = None


def get_csv_loader(csv_dir: str = None) -> CSVDataLoader:
    """Get or create the CSV loader singleton."""
    global _csv_loader
    
    if _csv_loader is None:
        _csv_loader = CSVDataLoader(csv_dir)
    
    return _csv_loader


def get_character_csv_info(character_id: str) -> dict:
    """Convenience function to get character info from CSV."""
    loader = get_csv_loader()
    return loader.get_character_info_dict(character_id)


def get_skill_csv_info(skill_id: str) -> dict:
    """Convenience function to get skill info from CSV."""
    loader = get_csv_loader()
    return loader.get_skill_info_dict(skill_id)
