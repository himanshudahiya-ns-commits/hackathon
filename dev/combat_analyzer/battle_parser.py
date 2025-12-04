"""
Battle Log Parser Module
Parses raw battle log text files and extracts structured data.
"""
import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CharacterStats:
    """Character stats at battle start."""
    name: str
    team: str  # LEFT or RIGHT
    level: int = 1
    quality: int = 1
    evolution: int = 1
    health: int = 0
    max_health: int = 0
    attack: int = 0
    defense: int = 0
    speed: int = 0
    critical_chance: float = 0.0
    dodge_chance: float = 0.0
    counter_chance: float = 0.0
    lifesteal: float = 0.0
    piercing: float = 0.0
    archetype: str = ""
    skills: list = field(default_factory=list)
    tags: list = field(default_factory=list)


@dataclass
class DamageEvent:
    """A damage event in battle."""
    turn: int
    attacker: str
    target: str
    skill_id: str
    damage: int
    attacker_attack: int
    target_defense: int
    skill_power: str
    is_critical: bool = False


@dataclass
class HealEvent:
    """A heal event in battle."""
    turn: int
    healer: str
    target: str
    amount: int


@dataclass
class KOEvent:
    """A KO (knockout) event."""
    turn: int
    character: str


@dataclass
class BuffDebuffEvent:
    """A buff or debuff application."""
    turn: int
    source: str
    target: str
    stat: str
    amount: float
    is_buff: bool
    status_name: str = ""


@dataclass
class TurnEvent:
    """A turn start event."""
    turn_number: int
    owner: str
    team_health: dict = field(default_factory=dict)


@dataclass
class BattleResult:
    """Final battle result."""
    won: bool
    winner_team: str
    total_turns: int
    stars: int
    final_health: dict = field(default_factory=dict)


@dataclass
class ParsedBattle:
    """Complete parsed battle data."""
    seed: int
    game_mode: str
    left_team: list  # List of CharacterStats
    right_team: list  # List of CharacterStats
    turns: list  # List of TurnEvent
    damage_events: list  # List of DamageEvent
    heal_events: list  # List of HealEvent
    ko_events: list  # List of KOEvent
    buff_debuff_events: list  # List of BuffDebuffEvent
    result: BattleResult


class BattleLogParser:
    """Parser for battle log text files."""
    
    def __init__(self):
        self.current_turn = 0
    
    def parse_file(self, file_path: str) -> ParsedBattle:
        """Parse a battle log file and return structured data."""
        with open(file_path, 'r') as f:
            content = f.read()
        return self.parse(content)
    
    def parse(self, content: str) -> ParsedBattle:
        """Parse battle log content."""
        self.current_turn = 0
        
        # Extract basic info
        seed = self._extract_seed(content)
        game_mode = self._extract_game_mode(content)
        
        # Extract teams
        left_team = self._extract_team(content, "LEFT")
        right_team = self._extract_team(content, "RIGHT")
        
        # Extract events
        turns = self._extract_turns(content)
        damage_events = self._extract_damage_events(content)
        heal_events = self._extract_heal_events(content)
        ko_events = self._extract_ko_events(content)
        buff_debuff_events = self._extract_buff_debuff_events(content)
        
        # Extract result
        result = self._extract_result(content)
        
        return ParsedBattle(
            seed=seed,
            game_mode=game_mode,
            left_team=left_team,
            right_team=right_team,
            turns=turns,
            damage_events=damage_events,
            heal_events=heal_events,
            ko_events=ko_events,
            buff_debuff_events=buff_debuff_events,
            result=result
        )
    
    def _extract_seed(self, content: str) -> int:
        """Extract battle seed."""
        match = re.search(r'Seed:\s*(\d+)', content)
        return int(match.group(1)) if match else 0
    
    def _extract_game_mode(self, content: str) -> str:
        """Extract game mode."""
        match = re.search(r'--- Game Mode ---\s*\n(\w+)', content)
        return match.group(1) if match else "Unknown"
    
    def _extract_team(self, content: str, team_side: str) -> list:
        """Extract team characters with their stats."""
        characters = []
        
        # Find BattleStartFlowEvent section
        battle_start_match = re.search(r'\[BattleStartFlowEvent\](.*?)(?=\[CharacterToggleSkillFlowEvent\]|\[StateChangePrankFlowEvent\])', content, re.DOTALL)
        if not battle_start_match:
            return characters
        
        battle_start_section = battle_start_match.group(1)
        
        # Split by character blocks (each starts with <character_name>)
        char_blocks = re.split(r'(?=<\w+>)', battle_start_section)
        
        for block in char_blocks:
            if not block.strip():
                continue
            
            # Check if this character is on the requested team
            team_match = re.search(r'Team:\s*(\w+)', block)
            if not team_match or team_match.group(1) != team_side:
                continue
            
            char = self._parse_character_block(block)
            if char:
                characters.append(char)
        
        return characters
    
    def _parse_character_block(self, block: str) -> Optional[CharacterStats]:
        """Parse a single character block."""
        # Extract name and level info
        name_match = re.search(r'<(\w+)>\s*\(L:(\d+)\|Q:(\d+)\|E:(\d+)\)', block)
        if not name_match:
            return None
        
        name = name_match.group(1)
        level = int(name_match.group(2))
        quality = int(name_match.group(3))
        evolution = int(name_match.group(4))
        
        # Extract team
        team_match = re.search(r'Team:\s*(\w+)', block)
        team = team_match.group(1) if team_match else "UNKNOWN"
        
        # Extract stats
        health_match = re.search(r'Health:\s*(\d+)/(\d+)', block)
        attack_match = re.search(r'Attack:\s*(\d+)/(\d+)', block)
        defense_match = re.search(r'Defense:\s*(\d+)/(\d+)', block)
        speed_match = re.search(r'Speed:\s*(\d+)/(\d+)', block)
        crit_match = re.search(r'Critical Chance:\s*([\d.]+)%', block)
        dodge_match = re.search(r'Dodge Chance:\s*([\d.]+)%', block)
        counter_match = re.search(r'Counter Chance:\s*([\d.]+)%', block)
        lifesteal_match = re.search(r'Lifesteal:\s*([\d.]+)%', block)
        piercing_match = re.search(r'Piercing:\s*([\d.]+)%', block)
        
        # Extract archetype from tags
        archetype = ""
        archetype_match = re.search(r'tag_archetype_(\w+):', block)
        if archetype_match:
            archetype = archetype_match.group(1)
        
        # Extract skills
        skills = []
        skill_matches = re.findall(r'\*\s*\((\w+)\)\s*(skill_\w+)', block)
        for skill_type, skill_id in skill_matches:
            skills.append({"type": skill_type, "id": skill_id})
        
        # Extract tags
        tags = []
        tag_matches = re.findall(r'\*\s*([\w_]+):\s*\d+\s*-\s*Age:', block)
        tags = tag_matches
        
        return CharacterStats(
            name=name,
            team=team,
            level=level,
            quality=quality,
            evolution=evolution,
            health=int(health_match.group(1)) if health_match else 0,
            max_health=int(health_match.group(2)) if health_match else 0,
            attack=int(attack_match.group(1)) if attack_match else 0,
            defense=int(defense_match.group(1)) if defense_match else 0,
            speed=int(speed_match.group(1)) if speed_match else 0,
            critical_chance=float(crit_match.group(1)) / 100 if crit_match else 0,
            dodge_chance=float(dodge_match.group(1)) / 100 if dodge_match else 0,
            counter_chance=float(counter_match.group(1)) / 100 if counter_match else 0,
            lifesteal=float(lifesteal_match.group(1)) / 100 if lifesteal_match else 0,
            piercing=float(piercing_match.group(1)) / 100 if piercing_match else 0,
            archetype=archetype,
            skills=skills,
            tags=tags
        )
    
    def _extract_turns(self, content: str) -> list:
        """Extract turn events."""
        turns = []
        
        # Find all turn start events
        turn_pattern = r'\[TurnStartFlowEvent\]\s*Turn owner:\s*(\w+)\s*\|\s*Turn:\s*(\d+)'
        matches = re.finditer(turn_pattern, content)
        
        for match in matches:
            owner = match.group(1)
            turn_num = int(match.group(2))
            
            # Try to find team health for this turn (look backwards for health info)
            pos = match.start()
            health_section = content[max(0, pos-500):pos]
            health_match = re.search(r'Left Team:\s*([^\n]+)\s*\nRight Team:\s*([^\n]+)', health_section)
            
            team_health = {}
            if health_match:
                # Parse left team health
                left_health = health_match.group(1)
                for h in re.finditer(r'(\w+)\s*\((\d+)/(\d+)\)', left_health):
                    team_health[h.group(1)] = {"current": int(h.group(2)), "max": int(h.group(3))}
                
                # Parse right team health
                right_health = health_match.group(2)
                for h in re.finditer(r'(\w+)\s*\((\d+)/(\d+)\)', right_health):
                    team_health[h.group(1)] = {"current": int(h.group(2)), "max": int(h.group(3))}
            
            turns.append(TurnEvent(
                turn_number=turn_num,
                owner=owner,
                team_health=team_health
            ))
        
        return turns
    
    def _extract_damage_events(self, content: str) -> list:
        """Extract all damage events."""
        events = []
        current_turn = 0
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Track current turn
            turn_match = re.search(r'\[TurnStartFlowEvent\].*Turn:\s*(\d+)', line)
            if turn_match:
                current_turn = int(turn_match.group(1))
            
            # Parse damage lines
            # Format: Damage: (attacker) -> (target (hp/max)); Attack (Base) X (Current) Y; SkillPower Z%; Attack with Variance W; Defense D; Total Damage T
            damage_match = re.search(
                r'Damage:\s*\((\w+)\)\s*->\s*\((\w+)\s*\((\d+)/(\d+)\)\);\s*Attack\s*\(Base\)\s*(\d+)\s*\(Current\)\s*([\d.]+);\s*SkillPower\s*([\d.]+)%.*?Defense\s*([\d.]+);\s*Total Damage\s*(\d+)',
                line
            )
            
            if damage_match:
                # Find the skill used (look at previous lines for skill event)
                skill_id = "unknown"
                for j in range(max(0, i-10), i):
                    skill_match = re.search(r'\[CharacterSkillPrankFlowEvent\].*\(active\)\s*(skill_\w+)', lines[j])
                    if skill_match:
                        skill_id = skill_match.group(1)
                
                events.append(DamageEvent(
                    turn=current_turn,
                    attacker=damage_match.group(1),
                    target=damage_match.group(2),
                    skill_id=skill_id,
                    damage=int(damage_match.group(9)),
                    attacker_attack=int(float(damage_match.group(6))),
                    target_defense=int(float(damage_match.group(8))),
                    skill_power=f"{damage_match.group(7)}%"
                ))
        
        return events
    
    def _extract_heal_events(self, content: str) -> list:
        """Extract all heal events."""
        events = []
        current_turn = 0
        
        for line in content.split('\n'):
            # Track current turn
            turn_match = re.search(r'\[TurnStartFlowEvent\].*Turn:\s*(\d+)', line)
            if turn_match:
                current_turn = int(turn_match.group(1))
            
            # Parse heal lines
            heal_match = re.search(r'Heal:\s*(\w+)\s*-\s*Amount:\s*(\d+)', line)
            if heal_match:
                events.append(HealEvent(
                    turn=current_turn,
                    healer="",  # Could be extracted from context
                    target=heal_match.group(1),
                    amount=int(heal_match.group(2))
                ))
        
        return events
    
    def _extract_ko_events(self, content: str) -> list:
        """Extract all KO events."""
        events = []
        
        # Pattern: [KOPrankFlowEvent] KO => character | Turn: X
        ko_pattern = r'\[KOPrankFlowEvent\]\s*KO\s*=>\s*(\w+)\s*\|\s*Turn:\s*(\d+)'
        matches = re.finditer(ko_pattern, content)
        
        for match in matches:
            events.append(KOEvent(
                turn=int(match.group(2)),
                character=match.group(1)
            ))
        
        return events
    
    def _extract_buff_debuff_events(self, content: str) -> list:
        """Extract buff/debuff events."""
        events = []
        current_turn = 0
        
        for line in content.split('\n'):
            # Track current turn
            turn_match = re.search(r'\[TurnStartFlowEvent\].*Turn:\s*(\d+)', line)
            if turn_match:
                current_turn = int(turn_match.group(1))
            
            # Parse status effect additions
            # Format: Added: StatusName (duration) (source) -> (target)
            status_match = re.search(r'Added:\s*(\w+)\s*\(\d+\)\s*\((\w+)\)\s*->\s*\((\w+)\)', line)
            if status_match:
                status_name = status_match.group(1)
                is_buff = "Up" in status_name or "Buff" in status_name
                events.append(BuffDebuffEvent(
                    turn=current_turn,
                    source=status_match.group(2),
                    target=status_match.group(3),
                    stat=status_name,
                    amount=0,
                    is_buff=is_buff,
                    status_name=status_name
                ))
            
            # Parse stat changes
            # Format: Change stat (mult/flat): target - Stat: StatName - Amount: X (from -> to)
            stat_change_match = re.search(
                r'Change stat \((\w+)\):\s*(\w+)\s*-\s*Stat:\s*(\w+)\s*-\s*Amount:\s*([-\d.]+)',
                line
            )
            if stat_change_match:
                amount = float(stat_change_match.group(4))
                is_buff = amount > 0
                events.append(BuffDebuffEvent(
                    turn=current_turn,
                    source="",
                    target=stat_change_match.group(2),
                    stat=stat_change_match.group(3),
                    amount=amount,
                    is_buff=is_buff
                ))
        
        return events
    
    def _extract_result(self, content: str) -> BattleResult:
        """Extract battle result."""
        # Look for the JSON result at the end
        json_match = re.search(r'"BattleWon":\s*"(\w+)"', content)
        won = json_match.group(1).lower() == "true" if json_match else False
        
        # Extract winner
        winner_match = re.search(r'Battle Winner:\s*(\w+)', content)
        winner_team = winner_match.group(1) if winner_match else "Unknown"
        
        # Extract total turns
        turns_match = re.search(r'Total Battle Turns:\s*(\d+)', content)
        total_turns = int(turns_match.group(1)) if turns_match else 0
        
        # Extract stars
        stars_match = re.search(r'Battle Stars:\s*(\d+)', content)
        stars = int(stars_match.group(1)) if stars_match else 0
        
        # Extract final health from BattleEnd section
        final_health = {}
        end_match = re.search(r'\[StateChangePrankFlowEvent\].*\(BattleEnd\).*\nLeft Team:\s*([^\n]+)\s*\nRight Team:\s*([^\n]+)', content)
        if end_match:
            for h in re.finditer(r'(\w+)\s*\((\d+)/(\d+)\)', end_match.group(1)):
                final_health[h.group(1)] = {"current": int(h.group(2)), "max": int(h.group(3))}
            for h in re.finditer(r'(\w+)\s*\((\d+)/(\d+)\)', end_match.group(2)):
                final_health[h.group(1)] = {"current": int(h.group(2)), "max": int(h.group(3))}
        
        return BattleResult(
            won=won,
            winner_team=winner_team,
            total_turns=total_turns,
            stars=stars,
            final_health=final_health
        )


def parse_battle_log(file_path: str) -> ParsedBattle:
    """Convenience function to parse a battle log file."""
    parser = BattleLogParser()
    return parser.parse_file(file_path)


