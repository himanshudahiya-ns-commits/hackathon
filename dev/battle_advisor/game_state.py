"""
Game State Module
Manages the battle simulation state including characters, HP, buffs, skills, and turn order.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import copy


class Team(Enum):
    PLAYER = "player"
    ENEMY = "enemy"


class SkillType(Enum):
    SINGLE_TARGET = "single_target"
    AOE = "aoe"
    SELF = "self"
    ALLY = "ally"
    ALL_ALLIES = "all_allies"


@dataclass
class Skill:
    """Represents a character skill."""
    skill_id: str
    name: str
    skill_type: SkillType = SkillType.SINGLE_TARGET
    power: int = 100  # Damage/heal percentage
    cooldown: int = 0  # Turns until available
    max_cooldown: int = 0  # Original cooldown
    description: str = ""
    effects: List[str] = field(default_factory=list)  # e.g., ["stun", "attack_down"]
    is_passive: bool = False
    
    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "type": self.skill_type.value,
            "power": self.power,
            "cooldown": self.cooldown,
            "max_cooldown": self.max_cooldown,
            "description": self.description,
            "effects": self.effects,
            "is_available": self.cooldown == 0 and not self.is_passive
        }


@dataclass
class StatusEffect:
    """Represents a buff or debuff."""
    name: str
    duration: int  # Turns remaining
    stacks: int = 1
    is_buff: bool = True
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "stacks": self.stacks,
            "is_buff": self.is_buff
        }


@dataclass
class Character:
    """Represents a character in battle."""
    character_id: str
    name: str
    team: Team
    
    # Stats
    max_hp: int = 100
    current_hp: int = 100
    attack: int = 50
    defense: int = 50
    speed: int = 50
    
    # Character info
    archetype: str = "Attacker"  # Attacker, Defender, Support
    rarity: str = "Common"
    level: int = 1
    
    # Battle state
    skills: List[Skill] = field(default_factory=list)
    status_effects: List[StatusEffect] = field(default_factory=list)
    is_alive: bool = True
    has_taunt: bool = False
    is_stunned: bool = False
    is_silenced: bool = False
    
    def take_damage(self, amount: int) -> int:
        """Apply damage and return actual damage dealt."""
        # Factor in defense (simple formula)
        actual_damage = max(1, amount - (self.defense // 10))
        self.current_hp = max(0, self.current_hp - actual_damage)
        if self.current_hp <= 0:
            self.is_alive = False
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Heal and return actual healing done."""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp
    
    def add_status(self, effect: StatusEffect):
        """Add a status effect."""
        # Check if already exists, stack or refresh
        for existing in self.status_effects:
            if existing.name == effect.name:
                existing.duration = max(existing.duration, effect.duration)
                existing.stacks += effect.stacks
                return
        self.status_effects.append(effect)
        
        # Update flags
        if effect.name.lower() == "taunt":
            self.has_taunt = True
        elif effect.name.lower() == "stun":
            self.is_stunned = True
        elif effect.name.lower() == "silence":
            self.is_silenced = True
    
    def tick_status_effects(self):
        """Reduce duration of all status effects at turn end."""
        remaining = []
        for effect in self.status_effects:
            effect.duration -= 1
            if effect.duration > 0:
                remaining.append(effect)
            else:
                # Remove flags
                if effect.name.lower() == "taunt":
                    self.has_taunt = False
                elif effect.name.lower() == "stun":
                    self.is_stunned = False
                elif effect.name.lower() == "silence":
                    self.is_silenced = False
        self.status_effects = remaining
    
    def get_available_skills(self) -> List[Skill]:
        """Get skills that can be used this turn."""
        if self.is_stunned or self.is_silenced:
            # Only basic attack available
            return [s for s in self.skills if s.skill_id.endswith("_basic")]
        return [s for s in self.skills if s.cooldown == 0 and not s.is_passive]
    
    def use_skill(self, skill: Skill):
        """Put skill on cooldown after use."""
        skill.cooldown = skill.max_cooldown
    
    def tick_cooldowns(self):
        """Reduce all skill cooldowns by 1."""
        for skill in self.skills:
            if skill.cooldown > 0:
                skill.cooldown -= 1
    
    @property
    def hp_percent(self) -> float:
        return (self.current_hp / self.max_hp) * 100 if self.max_hp > 0 else 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.character_id,
            "name": self.name,
            "team": self.team.value,
            "hp": self.current_hp,
            "max_hp": self.max_hp,
            "hp_percent": round(self.hp_percent, 1),
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "archetype": self.archetype,
            "rarity": self.rarity,
            "level": self.level,
            "is_alive": self.is_alive,
            "status_effects": [e.to_dict() for e in self.status_effects],
            "is_stunned": self.is_stunned,
            "is_silenced": self.is_silenced,
            "has_taunt": self.has_taunt
        }


@dataclass
class TurnAction:
    """Represents an action taken during a turn."""
    actor: Character
    skill: Skill
    target: Optional[Character]
    damage_dealt: int = 0
    healing_done: int = 0
    effects_applied: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "actor": self.actor.name,
            "skill": self.skill.name,
            "target": self.target.name if self.target else None,
            "damage_dealt": self.damage_dealt,
            "healing_done": self.healing_done,
            "effects_applied": self.effects_applied
        }


@dataclass
class BattleLog:
    """Log of all actions in the battle."""
    actions: List[TurnAction] = field(default_factory=list)
    
    def add(self, action: TurnAction):
        self.actions.append(action)
    
    def get_recent(self, n: int = 5) -> List[TurnAction]:
        return self.actions[-n:]


class GameState:
    """
    Manages the complete battle state.
    Handles turn order, applying skills, and tracking victory conditions.
    """
    
    def __init__(self):
        self.characters: List[Character] = []
        self.turn_number: int = 0
        self.current_actor_index: int = 0
        self.turn_order: List[Character] = []
        self.battle_log: BattleLog = BattleLog()
        self.is_battle_over: bool = False
        self.winner: Optional[Team] = None
    
    def add_character(self, character: Character):
        """Add a character to the battle."""
        self.characters.append(character)
    
    def initialize_battle(self):
        """Set up turn order based on speed."""
        self.turn_order = sorted(
            [c for c in self.characters if c.is_alive],
            key=lambda c: c.speed,
            reverse=True
        )
        self.turn_number = 1
        self.current_actor_index = 0
    
    @property
    def current_actor(self) -> Optional[Character]:
        """Get the character whose turn it is."""
        if not self.turn_order:
            return None
        # Skip dead characters
        while self.current_actor_index < len(self.turn_order):
            actor = self.turn_order[self.current_actor_index]
            if actor.is_alive:
                return actor
            self.current_actor_index += 1
        return None
    
    def get_player_characters(self) -> List[Character]:
        """Get all player team characters."""
        return [c for c in self.characters if c.team == Team.PLAYER]
    
    def get_enemy_characters(self) -> List[Character]:
        """Get all enemy team characters."""
        return [c for c in self.characters if c.team == Team.ENEMY]
    
    def get_alive_characters(self, team: Team) -> List[Character]:
        """Get alive characters for a team."""
        return [c for c in self.characters if c.team == team and c.is_alive]
    
    def get_allies_of(self, character: Character) -> List[Character]:
        """Get allies of a character (excluding self)."""
        return [c for c in self.characters 
                if c.team == character.team and c != character and c.is_alive]
    
    def get_enemies_of(self, character: Character) -> List[Character]:
        """Get enemies of a character."""
        enemy_team = Team.ENEMY if character.team == Team.PLAYER else Team.PLAYER
        return [c for c in self.characters if c.team == enemy_team and c.is_alive]
    
    def get_valid_targets(self, actor: Character, skill: Skill) -> List[Character]:
        """Get valid targets for a skill."""
        if skill.skill_type == SkillType.SELF:
            return [actor]
        elif skill.skill_type == SkillType.ALLY:
            return self.get_allies_of(actor)
        elif skill.skill_type == SkillType.ALL_ALLIES:
            return [actor] + self.get_allies_of(actor)
        else:
            # Damage skills target enemies
            enemies = self.get_enemies_of(actor)
            # Check for taunt
            taunters = [e for e in enemies if e.has_taunt]
            if taunters and skill.skill_type == SkillType.SINGLE_TARGET:
                return taunters
            return enemies
    
    def find_character(self, character_id: str) -> Optional[Character]:
        """Find a character by ID."""
        for c in self.characters:
            if c.character_id == character_id:
                return c
        return None
    
    def apply_skill(self, actor: Character, skill: Skill, target: Optional[Character]) -> TurnAction:
        """Apply a skill and return the action result."""
        action = TurnAction(actor=actor, skill=skill, target=target)
        
        # Calculate damage/healing based on skill type
        if skill.skill_type in [SkillType.SINGLE_TARGET, SkillType.AOE]:
            targets = [target] if skill.skill_type == SkillType.SINGLE_TARGET else self.get_enemies_of(actor)
            
            for t in targets:
                if t and t.is_alive:
                    # Calculate damage: (attack * power%) - defense factor
                    base_damage = int(actor.attack * (skill.power / 100))
                    damage = t.take_damage(base_damage)
                    action.damage_dealt += damage
                    
                    # Apply effects
                    for effect_name in skill.effects:
                        if effect_name in ["stun", "silence", "attack_down", "defense_down", "speed_down"]:
                            t.add_status(StatusEffect(name=effect_name, duration=2, is_buff=False))
                            action.effects_applied.append(f"{effect_name} on {t.name}")
        
        elif skill.skill_type in [SkillType.SELF, SkillType.ALLY, SkillType.ALL_ALLIES]:
            targets = self.get_valid_targets(actor, skill)
            for t in targets:
                if t and t.is_alive:
                    # Healing skill
                    heal_amount = int(t.max_hp * (skill.power / 100))
                    healed = t.heal(heal_amount)
                    action.healing_done += healed
                    
                    # Apply buff effects
                    for effect_name in skill.effects:
                        if effect_name in ["attack_up", "defense_up", "speed_up", "taunt"]:
                            t.add_status(StatusEffect(name=effect_name, duration=2, is_buff=True))
                            action.effects_applied.append(f"{effect_name} on {t.name}")
        
        # Put skill on cooldown
        actor.use_skill(skill)
        
        # Log the action
        self.battle_log.add(action)
        
        return action
    
    def advance_turn(self):
        """Move to the next turn."""
        if self.current_actor:
            # Tick cooldowns and status effects
            self.current_actor.tick_cooldowns()
            self.current_actor.tick_status_effects()
        
        # Move to next actor
        self.current_actor_index += 1
        
        # Check if round is complete
        if self.current_actor_index >= len(self.turn_order):
            self.turn_number += 1
            self.current_actor_index = 0
            # Refresh turn order (in case someone died or speed changed)
            self.turn_order = sorted(
                [c for c in self.characters if c.is_alive],
                key=lambda c: c.speed,
                reverse=True
            )
        
        # Check victory conditions
        self._check_battle_end()
    
    def _check_battle_end(self):
        """Check if battle is over."""
        player_alive = any(c.is_alive for c in self.get_player_characters())
        enemy_alive = any(c.is_alive for c in self.get_enemy_characters())
        
        if not player_alive:
            self.is_battle_over = True
            self.winner = Team.ENEMY
        elif not enemy_alive:
            self.is_battle_over = True
            self.winner = Team.PLAYER
    
    def is_over(self) -> bool:
        """Check if battle has ended."""
        return self.is_battle_over
    
    def build_turn_state(self) -> dict:
        """Build the current turn state for AI analysis."""
        actor = self.current_actor
        if not actor:
            return {}
        
        return {
            "turn_number": self.turn_number,
            "actor": actor.to_dict(),
            "actor_skills": [s.to_dict() for s in actor.get_available_skills()],
            "allies": [c.to_dict() for c in self.get_allies_of(actor)],
            "enemies": [c.to_dict() for c in self.get_enemies_of(actor)],
            "recent_actions": [a.to_dict() for a in self.battle_log.get_recent(3)],
            "battle_context": {
                "player_alive": len(self.get_alive_characters(Team.PLAYER)),
                "enemy_alive": len(self.get_alive_characters(Team.ENEMY)),
                "turn_order": [c.name for c in self.turn_order if c.is_alive]
            }
        }
    
    def get_battle_summary(self) -> str:
        """Get a text summary of current battle state."""
        lines = [f"\n{'='*50}", f"TURN {self.turn_number}", f"{'='*50}"]
        
        # Current actor
        actor = self.current_actor
        if actor:
            lines.append(f"\n🎯 Current Turn: {actor.name} ({actor.team.value})")
            lines.append(f"   HP: {actor.current_hp}/{actor.max_hp} ({actor.hp_percent:.0f}%)")
        
        # Player team
        lines.append("\n👤 PLAYER TEAM:")
        for c in self.get_player_characters():
            status = "💀" if not c.is_alive else "✅"
            effects = ", ".join([e.name for e in c.status_effects]) or "none"
            lines.append(f"   {status} {c.name}: {c.current_hp}/{c.max_hp} HP | Effects: {effects}")
        
        # Enemy team
        lines.append("\n👹 ENEMY TEAM:")
        for c in self.get_enemy_characters():
            status = "💀" if not c.is_alive else "⚔️"
            effects = ", ".join([e.name for e in c.status_effects]) or "none"
            lines.append(f"   {status} {c.name}: {c.current_hp}/{c.max_hp} HP | Effects: {effects}")
        
        return "\n".join(lines)
