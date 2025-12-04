"""
Metrics Computation Module
Computes battle metrics from parsed battle data.
"""
from dataclasses import dataclass, field
from typing import Optional
from .battle_parser import ParsedBattle, CharacterStats


@dataclass
class CharacterMetrics:
    """Computed metrics for a single character."""
    name: str
    team: str
    archetype: str
    level: int
    
    # Combat stats
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    total_healing_done: int = 0
    total_healing_received: int = 0
    
    # Turn stats
    turns_taken: int = 0
    first_turn_number: Optional[int] = None
    
    # KO info
    was_ko: bool = False
    ko_turn: Optional[int] = None
    kills: int = 0
    
    # Status effects
    buffs_received: int = 0
    debuffs_received: int = 0
    buffs_applied: int = 0
    debuffs_applied: int = 0
    
    # Starting stats
    starting_health: int = 0
    starting_attack: int = 0
    starting_defense: int = 0
    starting_speed: int = 0
    
    # Final state
    final_health: int = 0
    final_health_percent: float = 0.0


@dataclass
class TeamMetrics:
    """Aggregated metrics for a team."""
    team_name: str  # LEFT or RIGHT
    
    # Aggregate stats
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    total_healing: int = 0
    
    # Average stats
    avg_attack: float = 0.0
    avg_defense: float = 0.0
    avg_speed: float = 0.0
    avg_health: float = 0.0
    
    # Team composition
    character_count: int = 0
    archetypes: list = field(default_factory=list)
    
    # Turn control
    total_turns: int = 0
    first_turn: bool = False
    
    # KO stats
    characters_ko: int = 0
    characters_alive: int = 0
    
    # Status effects
    total_buffs: int = 0
    total_debuffs_received: int = 0


@dataclass
class BattleMetrics:
    """Complete battle metrics."""
    # Result
    result: str  # WIN or LOSS (from player perspective - LEFT team)
    winner_team: str
    total_turns: int
    stars: int
    
    # Team metrics
    player_team: TeamMetrics
    enemy_team: TeamMetrics
    
    # Character metrics
    player_characters: list  # List of CharacterMetrics
    enemy_characters: list  # List of CharacterMetrics
    
    # Key events
    first_ko: Optional[dict] = None  # {character, turn, team}
    biggest_hit: Optional[dict] = None  # {attacker, target, damage, turn}
    turn_order: list = field(default_factory=list)  # Order of first turns
    
    # Stat comparisons
    speed_advantage: str = ""  # "player", "enemy", or "even"
    attack_advantage: str = ""
    defense_advantage: str = ""
    health_advantage: str = ""
    
    # Key insights
    key_moments: list = field(default_factory=list)


class MetricsComputer:
    """Computes metrics from parsed battle data."""
    
    def compute(self, battle: ParsedBattle) -> BattleMetrics:
        """Compute all metrics from parsed battle."""
        # Initialize character metrics
        player_chars = self._init_character_metrics(battle.left_team)
        enemy_chars = self._init_character_metrics(battle.right_team)
        
        all_chars = {c.name: c for c in player_chars + enemy_chars}
        
        # Process damage events
        for event in battle.damage_events:
            attacker = event.attacker.replace('_l', '').replace('_r', '')
            target = event.target.replace('_l', '').replace('_r', '')
            
            if attacker in all_chars:
                all_chars[attacker].total_damage_dealt += event.damage
            if target in all_chars:
                all_chars[target].total_damage_taken += event.damage
        
        # Process heal events
        for event in battle.heal_events:
            target = event.target.replace('_l', '').replace('_r', '')
            if target in all_chars:
                all_chars[target].total_healing_received += event.amount
        
        # Process KO events
        for event in battle.ko_events:
            char_name = event.character.replace('_l', '').replace('_r', '')
            if char_name in all_chars:
                all_chars[char_name].was_ko = True
                all_chars[char_name].ko_turn = event.turn
        
        # Process turns
        turn_order = []
        for turn in battle.turns:
            owner = turn.owner.replace('_l', '').replace('_r', '')
            if owner in all_chars:
                all_chars[owner].turns_taken += 1
                if all_chars[owner].first_turn_number is None:
                    all_chars[owner].first_turn_number = turn.turn_number
                    turn_order.append({"character": owner, "turn": turn.turn_number, "team": all_chars[owner].team})
        
        # Process buff/debuff events
        for event in battle.buff_debuff_events:
            target = event.target.replace('_l', '').replace('_r', '')
            source = event.source.replace('_l', '').replace('_r', '') if event.source else ""
            
            if target in all_chars:
                if event.is_buff:
                    all_chars[target].buffs_received += 1
                else:
                    all_chars[target].debuffs_received += 1
            
            if source and source in all_chars:
                if event.is_buff:
                    all_chars[source].buffs_applied += 1
                else:
                    all_chars[source].debuffs_applied += 1
        
        # Set final health from result
        for char_name, health_info in battle.result.final_health.items():
            clean_name = char_name.replace('_l', '').replace('_r', '')
            if clean_name in all_chars:
                all_chars[clean_name].final_health = health_info["current"]
                max_hp = health_info["max"]
                all_chars[clean_name].final_health_percent = (health_info["current"] / max_hp * 100) if max_hp > 0 else 0
        
        # Compute team metrics
        player_team = self._compute_team_metrics("LEFT", player_chars)
        enemy_team = self._compute_team_metrics("RIGHT", enemy_chars)
        
        # Determine first turn owner
        if turn_order:
            first_turn_team = turn_order[0]["team"]
            player_team.first_turn = first_turn_team == "LEFT"
            enemy_team.first_turn = first_turn_team == "RIGHT"
        
        # Find key events
        first_ko = None
        if battle.ko_events:
            ko = battle.ko_events[0]
            char_name = ko.character.replace('_l', '').replace('_r', '')
            team = "LEFT" if "_l" in ko.character else "RIGHT"
            first_ko = {"character": char_name, "turn": ko.turn, "team": team}
        
        biggest_hit = None
        if battle.damage_events:
            max_dmg = max(battle.damage_events, key=lambda x: x.damage)
            biggest_hit = {
                "attacker": max_dmg.attacker.replace('_l', '').replace('_r', ''),
                "target": max_dmg.target.replace('_l', '').replace('_r', ''),
                "damage": max_dmg.damage,
                "turn": max_dmg.turn,
                "skill": max_dmg.skill_id
            }
        
        # Compute advantages
        speed_adv = self._compute_advantage(player_team.avg_speed, enemy_team.avg_speed)
        attack_adv = self._compute_advantage(player_team.avg_attack, enemy_team.avg_attack)
        defense_adv = self._compute_advantage(player_team.avg_defense, enemy_team.avg_defense)
        health_adv = self._compute_advantage(player_team.avg_health, enemy_team.avg_health)
        
        # Generate key moments
        key_moments = self._generate_key_moments(battle, player_chars, enemy_chars, first_ko, biggest_hit)
        
        # Determine result from player (LEFT team) perspective
        result = "WIN" if battle.result.winner_team == "Team1" else "LOSS"
        
        return BattleMetrics(
            result=result,
            winner_team=battle.result.winner_team,
            total_turns=battle.result.total_turns,
            stars=battle.result.stars,
            player_team=player_team,
            enemy_team=enemy_team,
            player_characters=player_chars,
            enemy_characters=enemy_chars,
            first_ko=first_ko,
            biggest_hit=biggest_hit,
            turn_order=turn_order[:5],  # First 5 turns
            speed_advantage=speed_adv,
            attack_advantage=attack_adv,
            defense_advantage=defense_adv,
            health_advantage=health_adv,
            key_moments=key_moments
        )
    
    def _init_character_metrics(self, characters: list) -> list:
        """Initialize character metrics from parsed characters."""
        metrics = []
        for char in characters:
            m = CharacterMetrics(
                name=char.name,
                team=char.team,
                archetype=char.archetype,
                level=char.level,
                starting_health=char.max_health,
                starting_attack=char.attack,
                starting_defense=char.defense,
                starting_speed=char.speed
            )
            metrics.append(m)
        return metrics
    
    def _compute_team_metrics(self, team_name: str, characters: list) -> TeamMetrics:
        """Compute aggregated team metrics."""
        if not characters:
            return TeamMetrics(team_name=team_name)
        
        total_damage = sum(c.total_damage_dealt for c in characters)
        total_taken = sum(c.total_damage_taken for c in characters)
        total_healing = sum(c.total_healing_received for c in characters)
        
        avg_attack = sum(c.starting_attack for c in characters) / len(characters)
        avg_defense = sum(c.starting_defense for c in characters) / len(characters)
        avg_speed = sum(c.starting_speed for c in characters) / len(characters)
        avg_health = sum(c.starting_health for c in characters) / len(characters)
        
        archetypes = [c.archetype for c in characters if c.archetype]
        
        total_turns = sum(c.turns_taken for c in characters)
        ko_count = sum(1 for c in characters if c.was_ko)
        alive_count = len(characters) - ko_count
        
        total_buffs = sum(c.buffs_received for c in characters)
        total_debuffs = sum(c.debuffs_received for c in characters)
        
        return TeamMetrics(
            team_name=team_name,
            total_damage_dealt=total_damage,
            total_damage_taken=total_taken,
            total_healing=total_healing,
            avg_attack=avg_attack,
            avg_defense=avg_defense,
            avg_speed=avg_speed,
            avg_health=avg_health,
            character_count=len(characters),
            archetypes=archetypes,
            total_turns=total_turns,
            characters_ko=ko_count,
            characters_alive=alive_count,
            total_buffs=total_buffs,
            total_debuffs_received=total_debuffs
        )
    
    def _compute_advantage(self, player_val: float, enemy_val: float) -> str:
        """Determine which side has advantage."""
        if player_val == 0 and enemy_val == 0:
            return "even"
        
        diff_percent = ((player_val - enemy_val) / max(player_val, enemy_val)) * 100
        
        if diff_percent > 10:
            return "player"
        elif diff_percent < -10:
            return "enemy"
        else:
            return "even"
    
    def _generate_key_moments(self, battle: ParsedBattle, player_chars: list, 
                              enemy_chars: list, first_ko: dict, biggest_hit: dict) -> list:
        """Generate list of key battle moments."""
        moments = []
        
        # First KO
        if first_ko:
            team_label = "player" if first_ko["team"] == "LEFT" else "enemy"
            moments.append({
                "turn": first_ko["turn"],
                "type": "first_ko",
                "description": f"{first_ko['character']} ({team_label}) was knocked out on turn {first_ko['turn']}"
            })
        
        # Biggest hit
        if biggest_hit and biggest_hit["damage"] > 50:
            moments.append({
                "turn": biggest_hit["turn"],
                "type": "big_damage",
                "description": f"{biggest_hit['attacker']} dealt {biggest_hit['damage']} damage to {biggest_hit['target']} using {biggest_hit['skill']}"
            })
        
        # Early deaths (turn 1-2)
        for ko in battle.ko_events:
            if ko.turn <= 2:
                char_name = ko.character.replace('_l', '').replace('_r', '')
                moments.append({
                    "turn": ko.turn,
                    "type": "early_death",
                    "description": f"{char_name} died very early on turn {ko.turn}"
                })
        
        # Sort by turn
        moments.sort(key=lambda x: x["turn"])
        
        return moments


def compute_battle_metrics(battle: ParsedBattle) -> BattleMetrics:
    """Convenience function to compute metrics."""
    computer = MetricsComputer()
    return computer.compute(battle)
