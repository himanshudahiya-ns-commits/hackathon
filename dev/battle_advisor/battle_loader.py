"""
Battle Loader Module
Loads battle data from log files and CSV to create a GameState.
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from battle_advisor.game_state import GameState, Character, Skill, Team, SkillType, StatusEffect
from combat_analyzer.csv_helper import get_csv_loader, CSVDataLoader


class BattleLoader:
    """Loads battle data and creates GameState objects."""
    
    def __init__(self, csv_dir: str = None):
        """Initialize the battle loader."""
        self.csv_loader = get_csv_loader(csv_dir)
        self.csv_loader.load_all()
    
    def load_from_battle_log(self, log_path: str) -> GameState:
        """
        Load a battle from a log file.
        Parses initial stats and creates characters with skills.
        """
        game_state = GameState()
        
        with open(log_path, 'r') as f:
            content = f.read()
        
        # Parse characters from BattleStartFlowEvent
        left_team, right_team = self._parse_teams(content)
        
        # Add player team (left)
        for char_data in left_team:
            character = self._create_character(char_data, Team.PLAYER)
            game_state.add_character(character)
        
        # Add enemy team (right)
        for char_data in right_team:
            character = self._create_character(char_data, Team.ENEMY)
            game_state.add_character(character)
        
        # Initialize battle
        game_state.initialize_battle()
        
        return game_state
    
    def _parse_teams(self, content: str) -> Tuple[List[dict], List[dict]]:
        """Parse team data from battle log."""
        left_team = []
        right_team = []
        
        # Find BattleStartFlowEvent section
        start_match = re.search(r'\[BattleStartFlowEvent\](.*?)(?=\[TurnStartFlowEvent\]|\Z)', content, re.DOTALL)
        if not start_match:
            return left_team, right_team
        
        start_section = start_match.group(1)
        
        # Parse all characters in the section
        # Format: <character_id> (L:level|Q:quality|E:evolution)
        # Team: LEFT or RIGHT
        char_blocks = re.split(r'(?=<\w+>\s*\(L:\d+)', start_section)
        
        for block in char_blocks:
            if not block.strip():
                continue
            
            char_data = self._parse_character_block(block)
            if char_data:
                if char_data.get('team') == 'LEFT':
                    left_team.append(char_data)
                elif char_data.get('team') == 'RIGHT':
                    right_team.append(char_data)
        
        # Apply post-modification stats from first TurnStart (after onboarding buffs/debuffs)
        self._apply_turn_start_stats(content, left_team, right_team)
        
        return left_team, right_team
    
    def _apply_turn_start_stats(self, content: str, left_team: List[dict], right_team: List[dict]):
        """
        Apply the actual battle stats from the first TurnStart event.
        The game applies onboarding modifications that change stats significantly.
        """
        # Find first TurnStart state with HP values
        # Format: Left Team: bugs_bunny_l (156/156)
        #         Right Team: wile_e_coyote_r (100/100) | road_runner_r (40/40)
        turn_start_match = re.search(
            r'\[StateChangePrankFlowEvent\]\s*\(.*?\)\s*->\s*\(TurnStart\)\s*\n'
            r'Left Team:\s*([^\n]+)\n'
            r'Right Team:\s*([^\n]+)',
            content
        )
        
        if not turn_start_match:
            return
        
        left_line = turn_start_match.group(1)
        right_line = turn_start_match.group(2)
        
        # Parse HP values: character_id (current/max)
        hp_pattern = re.compile(r'(\w+)\s*\((\d+)/(\d+)\)')
        
        # Update left team HP
        for match in hp_pattern.finditer(left_line):
            char_id = match.group(1).replace('_l', '')  # Remove team suffix
            current_hp = int(match.group(2))
            max_hp = int(match.group(3))
            
            for char in left_team:
                if char['id'] == char_id:
                    char['health'] = max_hp
                    break
        
        # Update right team HP
        for match in hp_pattern.finditer(right_line):
            char_id = match.group(1).replace('_r', '')  # Remove team suffix
            current_hp = int(match.group(2))
            max_hp = int(match.group(3))
            
            for char in right_team:
                if char['id'] == char_id:
                    char['health'] = max_hp
                    break
        
        # Also try to get modified attack/defense/speed from stat change events
        self._apply_stat_modifications(content, left_team, right_team)
    
    def _apply_stat_modifications(self, content: str, left_team: List[dict], right_team: List[dict]):
        """
        Parse stat modifications from onboarding setup and apply final values.
        Look for the final stat values after all buffs/debuffs are applied.
        """
        # Find stat setup section - look for the flat stat additions which are the final values
        # Format: Change stat (flat): bugs_bunny_l - Stat: Attack - Amount: 57 (8 -> 57)
        flat_stat_pattern = re.compile(
            r'Change stat \(flat\):\s*(\w+)\s*-\s*Stat:\s*(\w+)\s*-\s*Amount:\s*[\d.-]+\s*\([^)]+\s*->\s*([\d.]+)\)'
        )
        
        # Collect final stats for each character
        char_stats = {}
        for match in flat_stat_pattern.finditer(content):
            char_ref = match.group(1)  # e.g., bugs_bunny_l
            stat_name = match.group(2).lower()  # e.g., attack
            final_value = float(match.group(3))
            
            # Remove team suffix
            char_id = re.sub(r'_[lr]$', '', char_ref)
            
            if char_id not in char_stats:
                char_stats[char_id] = {}
            
            # Map stat names
            stat_map = {
                'attack': 'attack',
                'defense': 'defense',
                'speed': 'speed',
                'maxhealth': 'health'
            }
            
            if stat_name in stat_map:
                char_stats[char_id][stat_map[stat_name]] = int(final_value)
        
        # Apply to teams
        for char in left_team + right_team:
            char_id = char['id']
            if char_id in char_stats:
                for stat, value in char_stats[char_id].items():
                    char[stat] = value
    
    def _parse_character_block(self, block: str) -> Optional[dict]:
        """Parse a single character block from the log."""
        # Extract character ID: <bugs_bunny>
        id_match = re.search(r'<(\w+)>', block)
        if not id_match:
            return None
        
        char_id = id_match.group(1)
        
        # Extract level: (L:1|Q:1|E:1)
        level_match = re.search(r'\(L:(\d+)', block)
        level = int(level_match.group(1)) if level_match else 1
        
        # Extract team: Team: LEFT or Team: RIGHT
        team_match = re.search(r'Team:\s*(LEFT|RIGHT)', block)
        team = team_match.group(1) if team_match else None
        
        # Extract stats: Health: 111/111, Attack: 40/40, etc.
        health_match = re.search(r'Health:\s*(\d+)/(\d+)', block)
        attack_match = re.search(r'Attack:\s*(\d+)/(\d+)', block)
        defense_match = re.search(r'Defense:\s*(\d+)/(\d+)', block)
        speed_match = re.search(r'Speed:\s*(\d+)/(\d+)', block)
        
        health = int(health_match.group(1)) if health_match else 100
        attack = int(attack_match.group(1)) if attack_match else 50
        defense = int(defense_match.group(1)) if defense_match else 50
        speed = int(speed_match.group(1)) if speed_match else 50
        
        # Extract archetype from tags: tag_archetype_attacker
        archetype_match = re.search(r'tag_archetype_(\w+)', block)
        archetype = archetype_match.group(1).title() if archetype_match else "Attacker"
        
        # Extract skills
        skills = []
        skill_matches = re.findall(r'\(Active\)\s*(skill_\w+)', block)
        skills.extend(skill_matches)
        passive_matches = re.findall(r'\(Passive\)\s*(skill_\w+)', block)
        skills.extend(passive_matches)
        
        return {
            'id': char_id,
            'level': level,
            'team': team,
            'health': health,
            'attack': attack,
            'defense': defense,
            'speed': speed,
            'archetype': archetype,
            'skills': skills
        }
    
    def _parse_team_section(self, section: str) -> List[dict]:
        """Parse individual team section (legacy method)."""
        characters = []
        
        # Pattern to match character entries
        char_pattern = re.compile(
            r'(\w+)\s*\((\w+)\)\s*-\s*Level:\s*(\d+).*?'
            r'Health:\s*(\d+).*?Attack:\s*(\d+).*?Defense:\s*(\d+).*?Speed:\s*(\d+)',
            re.DOTALL
        )
        
        for match in char_pattern.finditer(section):
            characters.append({
                'id': match.group(1),
                'archetype': match.group(2),
                'level': int(match.group(3)),
                'health': int(match.group(4)),
                'attack': int(match.group(5)),
                'defense': int(match.group(6)),
                'speed': int(match.group(7))
            })
        
        return characters
    
    def _create_character(self, char_data: dict, team: Team) -> Character:
        """Create a Character object from parsed data."""
        char_id = char_data['id']
        
        # Get additional info from CSV
        csv_info = self.csv_loader.get_character(char_id)
        display_name = csv_info.display_name if csv_info else char_id.replace('_', ' ').title()
        rarity = csv_info.rarity if csv_info else "Common"
        
        character = Character(
            character_id=char_id,
            name=display_name,
            team=team,
            max_hp=char_data['health'],
            current_hp=char_data['health'],
            attack=char_data['attack'],
            defense=char_data['defense'],
            speed=char_data['speed'],
            archetype=char_data.get('archetype', 'Attacker').title(),
            rarity=rarity,
            level=char_data['level']
        )
        
        # Load skills - prefer skills from log if available, otherwise from CSV
        log_skills = char_data.get('skills', [])
        if log_skills:
            skills = self._load_skills_from_ids(log_skills, char_id)
        else:
            skills = self._load_character_skills(char_id)
        
        character.skills = skills
        
        return character
    
    def _load_skills_from_ids(self, skill_ids: List[str], char_id: str) -> List[Skill]:
        """Load skills from specific skill IDs found in the log."""
        skills = []
        
        for skill_id in skill_ids:
            csv_skill = self.csv_loader.get_skill(skill_id)
            
            if csv_skill:
                skill_type = self._determine_skill_type(csv_skill.skill_type, csv_skill.description)
                power = self._extract_power(csv_skill.description)
                effects = self._extract_effects(csv_skill.description)
                cooldown = self._extract_cooldown(csv_skill.skill_type)
                
                skill = Skill(
                    skill_id=skill_id,
                    name=csv_skill.skill_name,
                    skill_type=skill_type,
                    power=power,
                    cooldown=0,
                    max_cooldown=cooldown,
                    description=csv_skill.description[:200] if csv_skill.description else "",
                    effects=effects,
                    is_passive=csv_skill.skill_type.lower() == "passive" if csv_skill.skill_type else False
                )
            else:
                # Create a basic skill if not found in CSV
                skill = Skill(
                    skill_id=skill_id,
                    name=skill_id.replace('skill_', '').replace('_', ' ').title(),
                    skill_type=SkillType.SINGLE_TARGET,
                    power=100,
                    description=f"Skill: {skill_id}"
                )
            
            skills.append(skill)
        
        # Ensure at least a basic attack
        if not skills or all(s.is_passive for s in skills):
            skills.insert(0, Skill(
                skill_id=f"{char_id}_basic",
                name="Basic Attack",
                skill_type=SkillType.SINGLE_TARGET,
                power=100,
                description="Deal 100% damage to target enemy."
            ))
        
        return skills[:5]  # Limit to 5 skills
    
    def _load_character_skills(self, char_id: str) -> List[Skill]:
        """Load skills for a character from CSV data."""
        skills = []
        csv_skills = self.csv_loader.get_character_skills(char_id)
        
        # Group skills by base name (without level suffix)
        skill_groups = {}
        for csv_skill in csv_skills:
            # Get base skill name (remove level number)
            base_name = re.sub(r'\s*\d+$', '', csv_skill.skill_name)
            if base_name not in skill_groups:
                skill_groups[base_name] = csv_skill
            elif csv_skill.is_max_level:
                skill_groups[base_name] = csv_skill
        
        # Create Skill objects for unique skills
        for base_name, csv_skill in skill_groups.items():
            skill_type = self._determine_skill_type(csv_skill.skill_type, csv_skill.description)
            power = self._extract_power(csv_skill.description)
            effects = self._extract_effects(csv_skill.description)
            cooldown = self._extract_cooldown(csv_skill.skill_type)
            
            skill = Skill(
                skill_id=csv_skill.skill_id,
                name=csv_skill.skill_name,
                skill_type=skill_type,
                power=power,
                cooldown=0,  # Start off cooldown
                max_cooldown=cooldown,
                description=csv_skill.description[:200],
                effects=effects,
                is_passive=csv_skill.skill_type.lower() == "passive"
            )
            skills.append(skill)
        
        # Ensure at least a basic attack
        if not skills or all(s.is_passive for s in skills):
            skills.insert(0, Skill(
                skill_id=f"{char_id}_basic",
                name="Basic Attack",
                skill_type=SkillType.SINGLE_TARGET,
                power=100,
                description="Deal 100% damage to target enemy."
            ))
        
        return skills[:5]  # Limit to 5 skills
    
    def _determine_skill_type(self, type_str: str, description: str) -> SkillType:
        """Determine skill type from metadata."""
        desc_lower = description.lower()
        
        if "all enemies" in desc_lower or "all team" in desc_lower:
            return SkillType.AOE
        elif "heal" in desc_lower and "all" in desc_lower:
            return SkillType.ALL_ALLIES
        elif "heal" in desc_lower or "grant" in desc_lower:
            if "self" in desc_lower or "this toon" in desc_lower:
                return SkillType.SELF
            return SkillType.ALLY
        else:
            return SkillType.SINGLE_TARGET
    
    def _extract_power(self, description: str) -> int:
        """Extract damage/heal percentage from description."""
        # Look for patterns like [110%], 110%, etc.
        match = re.search(r'\[?(\d+)%\]?', description)
        if match:
            return int(match.group(1))
        return 100
    
    def _extract_effects(self, description: str) -> List[str]:
        """Extract status effects from description."""
        effects = []
        desc_lower = description.lower()
        
        effect_keywords = {
            "stun": "stun",
            "silence": "silence",
            "attack up": "attack_up",
            "attack down": "attack_down",
            "defense up": "defense_up",
            "defense down": "defense_down",
            "speed up": "speed_up",
            "speed down": "speed_down",
            "taunt": "taunt",
            "heal": "heal",
            "damage over time": "dot",
            "heal over time": "hot"
        }
        
        for keyword, effect in effect_keywords.items():
            if keyword in desc_lower:
                effects.append(effect)
        
        return effects
    
    def _extract_cooldown(self, type_str: str) -> int:
        """Extract cooldown from skill type string."""
        # Pattern like "Active 2" or "Active 3 / 1"
        match = re.search(r'Active\s*(\d+)', type_str)
        if match:
            return int(match.group(1))
        return 0
    
    def create_sample_battle(self) -> GameState:
        """Create a sample battle for testing."""
        game_state = GameState()
        
        # Player team
        bugs = Character(
            character_id="bugs_bunny",
            name="Bugs Bunny",
            team=Team.PLAYER,
            max_hp=156,
            current_hp=156,
            attack=57,
            defense=51,
            speed=34,
            archetype="Attacker",
            rarity="Epic",
            level=30
        )
        bugs.skills = [
            Skill(
                skill_id="skill_safe_landing",
                name="Safe Landing",
                skill_type=SkillType.SINGLE_TARGET,
                power=100,
                max_cooldown=0,
                description="Deal 100% damage to target enemy, gaining Attack Up for 2 turns.",
                effects=["attack_up"]
            ),
            Skill(
                skill_id="skill_befuddle",
                name="Befuddle",
                skill_type=SkillType.SINGLE_TARGET,
                power=130,
                max_cooldown=2,
                description="Deal 130% damage to target enemy, inflicting 3 Defense Down and Silence.",
                effects=["defense_down", "silence"]
            ),
            Skill(
                skill_id="skill_explosive_surprise",
                name="Explosive Surprise",
                skill_type=SkillType.AOE,
                power=90,
                max_cooldown=3,
                description="Deal 90% damage to all enemies, inflicting 3 Defense Down to each.",
                effects=["defense_down"]
            )
        ]
        game_state.add_character(bugs)
        
        # Add Lola as ally
        lola = Character(
            character_id="lola_bunny",
            name="Lola Bunny",
            team=Team.PLAYER,
            max_hp=120,
            current_hp=120,
            attack=62,
            defense=38,
            speed=42,
            archetype="Attacker",
            rarity="Epic",
            level=28
        )
        lola.skills = [
            Skill(
                skill_id="skill_basketball_toss",
                name="Basketball Toss",
                skill_type=SkillType.SINGLE_TARGET,
                power=110,
                description="Deal 110% damage to target enemy."
            ),
            Skill(
                skill_id="skill_team_spirit",
                name="Team Spirit",
                skill_type=SkillType.ALL_ALLIES,
                power=20,
                max_cooldown=2,
                description="Grant all allies Attack Up and Speed Up for 2 turns.",
                effects=["attack_up", "speed_up"]
            )
        ]
        game_state.add_character(lola)
        
        # Enemy team
        wile = Character(
            character_id="wile_e_coyote",
            name="Wile E. Coyote",
            team=Team.ENEMY,
            max_hp=140,
            current_hp=140,
            attack=70,
            defense=45,
            speed=38,
            archetype="Attacker",
            rarity="Rare",
            level=32
        )
        wile.skills = [
            Skill(
                skill_id="skill_anvil_drop",
                name="Anvil Drop",
                skill_type=SkillType.SINGLE_TARGET,
                power=120,
                description="Deal 120% damage to target enemy."
            )
        ]
        game_state.add_character(wile)
        
        roadrunner = Character(
            character_id="road_runner",
            name="Road Runner",
            team=Team.ENEMY,
            max_hp=100,
            current_hp=100,
            attack=55,
            defense=35,
            speed=65,
            archetype="Support",
            rarity="Rare",
            level=30
        )
        roadrunner.skills = [
            Skill(
                skill_id="skill_meep_meep",
                name="Meep Meep",
                skill_type=SkillType.SINGLE_TARGET,
                power=80,
                description="Deal 80% damage and gain Speed Up.",
                effects=["speed_up"]
            )
        ]
        game_state.add_character(roadrunner)
        
        # Initialize battle
        game_state.initialize_battle()
        
        return game_state


def get_battle_loader(csv_dir: str = None) -> BattleLoader:
    """Get a battle loader instance."""
    return BattleLoader(csv_dir)
