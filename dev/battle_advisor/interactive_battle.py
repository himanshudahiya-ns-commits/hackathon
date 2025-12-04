"""
Interactive Battle Module
Provides a turn-by-turn interactive battle experience with AI recommendations.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from battle_advisor.game_state import GameState, Character, Skill, Team, SkillType
from battle_advisor.ai_advisor import AIAdvisor, get_ai_advisor
from battle_advisor.battle_loader import BattleLoader, get_battle_loader


class InteractiveBattle:
    """
    Interactive battle simulation with AI skill recommendations.
    """
    
    def __init__(self, game_state: GameState, ai_advisor: Optional[AIAdvisor] = None):
        """Initialize interactive battle."""
        self.game_state = game_state
        self.ai_advisor = ai_advisor or get_ai_advisor()
        self.auto_enemy = True  # Auto-play enemy turns
        self.show_ai_reasoning = True
    
    def run(self):
        """Run the interactive battle loop."""
        self._print_header()
        
        while not self.game_state.is_over():
            actor = self.game_state.current_actor
            if not actor:
                break
            
            # Show current state
            print(self.game_state.get_battle_summary())
            
            if actor.team == Team.PLAYER:
                self._handle_player_turn(actor)
            else:
                self._handle_enemy_turn(actor)
            
            # Advance to next turn
            self.game_state.advance_turn()
            
            # Pause between turns
            input("\n[Press Enter to continue...]")
        
        # Battle ended
        self._print_battle_result()
    
    def _print_header(self):
        """Print battle start header."""
        print("\n" + "="*60)
        print("⚔️  AI BATTLE ADVISOR - Interactive Battle Simulation  ⚔️")
        print("="*60)
        print("\nThe AI will recommend the best skill for each of your turns.")
        print("You can follow the recommendation or choose your own action.")
        print("-"*60)
    
    def _handle_player_turn(self, actor: Character):
        """Handle a player-controlled character's turn."""
        print(f"\n🎮 YOUR TURN: {actor.name}")
        print("-"*40)
        
        # Get available skills
        available_skills = actor.get_available_skills()
        if not available_skills:
            print("No skills available! (Stunned or Silenced)")
            return
        
        # Show available skills
        print("\n📋 Available Skills:")
        for i, skill in enumerate(available_skills, 1):
            cooldown_info = f" (CD: {skill.max_cooldown})" if skill.max_cooldown > 0 else ""
            print(f"  {i}. {skill.name}{cooldown_info}")
            print(f"     Type: {skill.skill_type.value} | Power: {skill.power}%")
            if skill.description:
                print(f"     {skill.description[:80]}...")
            if skill.effects:
                print(f"     Effects: {', '.join(skill.effects)}")
        
        # Get AI recommendation
        recommendation = None
        if self.ai_advisor:
            print("\n🤖 Getting AI recommendation...")
            turn_state = self.game_state.build_turn_state()
            recommendation = self.ai_advisor.get_recommendation(turn_state)
            
            if recommendation:
                self._display_recommendation(recommendation, available_skills)
        
        # Get player choice
        chosen_skill, chosen_target = self._get_player_choice(
            actor, available_skills, recommendation
        )
        
        if chosen_skill:
            # Apply the skill
            action = self.game_state.apply_skill(actor, chosen_skill, chosen_target)
            self._display_action_result(action)
    
    def _display_recommendation(self, recommendation: dict, available_skills: list):
        """Display the AI recommendation."""
        skill_id = recommendation.get("recommended_skill_id")
        target_id = recommendation.get("recommended_target_id")
        reason = recommendation.get("reason", "")
        
        # Find skill name
        skill_name = skill_id
        for skill in available_skills:
            if skill.skill_id == skill_id:
                skill_name = skill.name
                break
        
        # Find target name
        target_name = target_id
        if target_id:
            target = self.game_state.find_character(target_id)
            if target:
                target_name = target.name
        
        print("\n" + "="*50)
        print("🎯 AI RECOMMENDATION")
        print("="*50)
        print(f"  Skill:  {skill_name}")
        if target_name:
            print(f"  Target: {target_name}")
        print(f"\n  💡 Reason: {reason}")
        print("="*50)
    
    def _get_player_choice(self, actor: Character, available_skills: list, 
                           recommendation: dict = None) -> tuple:
        """Get the player's skill and target choice."""
        print("\n📌 Choose your action:")
        print("  [A] Accept AI recommendation")
        print("  [1-N] Choose skill by number")
        print("  [Q] Quit battle")
        
        while True:
            choice = input("\nYour choice: ").strip().upper()
            
            if choice == 'Q':
                print("Battle ended by player.")
                self.game_state.is_battle_over = True
                return None, None
            
            if choice == 'A' and recommendation:
                # Use AI recommendation
                skill_id = recommendation.get("recommended_skill_id")
                target_id = recommendation.get("recommended_target_id")
                
                skill = None
                for s in available_skills:
                    if s.skill_id == skill_id:
                        skill = s
                        break
                
                if not skill:
                    skill = available_skills[0]
                
                target = self.game_state.find_character(target_id) if target_id else None
                if not target and skill.skill_type == SkillType.SINGLE_TARGET:
                    enemies = self.game_state.get_enemies_of(actor)
                    target = enemies[0] if enemies else None
                
                return skill, target
            
            try:
                skill_index = int(choice) - 1
                if 0 <= skill_index < len(available_skills):
                    skill = available_skills[skill_index]
                    target = self._choose_target(actor, skill)
                    return skill, target
            except ValueError:
                pass
            
            print("Invalid choice. Try again.")
    
    def _choose_target(self, actor: Character, skill: Skill) -> Optional[Character]:
        """Let player choose a target for the skill."""
        valid_targets = self.game_state.get_valid_targets(actor, skill)
        
        if not valid_targets:
            return None
        
        if len(valid_targets) == 1:
            return valid_targets[0]
        
        if skill.skill_type in [SkillType.AOE, SkillType.ALL_ALLIES, SkillType.SELF]:
            return valid_targets[0]  # Target doesn't matter for these
        
        print("\n🎯 Choose target:")
        for i, target in enumerate(valid_targets, 1):
            hp_bar = self._get_hp_bar(target)
            print(f"  {i}. {target.name} {hp_bar}")
        
        while True:
            try:
                choice = int(input("Target #: ")) - 1
                if 0 <= choice < len(valid_targets):
                    return valid_targets[choice]
            except ValueError:
                pass
            print("Invalid target. Try again.")
    
    def _get_hp_bar(self, character: Character) -> str:
        """Get a visual HP bar for a character."""
        hp_pct = character.hp_percent
        filled = int(hp_pct / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {character.current_hp}/{character.max_hp}"
    
    def _display_health_status(self):
        """Display health status of all characters after an action."""
        print("\n" + "~"*40)
        print("📊 HEALTH STATUS")
        print("~"*40)
        
        # Player team
        print("👤 Player Team:")
        for char in self.game_state.get_player_characters():
            hp_bar = self._get_hp_bar(char)
            if char.is_alive:
                status_icon = "✅"
            else:
                status_icon = "💀"
            print(f"   {status_icon} {char.name}: {hp_bar} ({char.hp_percent:.0f}%)")
        
        # Enemy team
        print("👹 Enemy Team:")
        for char in self.game_state.get_enemy_characters():
            hp_bar = self._get_hp_bar(char)
            if char.is_alive:
                status_icon = "⚔️"
            else:
                status_icon = "💀"
            print(f"   {status_icon} {char.name}: {hp_bar} ({char.hp_percent:.0f}%)")
        
        print("~"*40)
    
    def _display_action_result(self, action):
        """Display the result of an action."""
        print("\n" + "-"*40)
        print(f"⚡ {action.actor.name} used {action.skill.name}!")
        
        if action.target:
            print(f"   Target: {action.target.name}")
        
        if action.damage_dealt > 0:
            print(f"   💥 Dealt {action.damage_dealt} damage!")
            if action.target and not action.target.is_alive:
                print(f"   💀 {action.target.name} was knocked out!")
        
        if action.healing_done > 0:
            print(f"   💚 Healed for {action.healing_done}!")
        
        if action.effects_applied:
            print(f"   ✨ Effects: {', '.join(action.effects_applied)}")
        
        # Show health status after action
        self._display_health_status()
    
    def _handle_enemy_turn(self, actor: Character):
        """Handle an enemy character's turn (AI-controlled)."""
        print(f"\n👹 ENEMY TURN: {actor.name}")
        print("-"*40)
        
        if actor.is_stunned:
            print(f"   {actor.name} is stunned and cannot act!")
            return
        
        available_skills = actor.get_available_skills()
        if not available_skills:
            print(f"   {actor.name} has no available skills!")
            return
        
        # Simple enemy AI: use first available skill on random target
        skill = available_skills[0]
        targets = self.game_state.get_valid_targets(actor, skill)
        
        if targets:
            # Target lowest HP player
            target = min(targets, key=lambda t: t.hp_percent)
            action = self.game_state.apply_skill(actor, skill, target)
            self._display_action_result(action)
        else:
            print(f"   {actor.name} has no valid targets!")
    
    def _print_battle_result(self):
        """Print the final battle result."""
        print("\n" + "="*60)
        if self.game_state.winner == Team.PLAYER:
            print("🏆 VICTORY! You won the battle!")
        else:
            print("💀 DEFEAT! You lost the battle.")
        print("="*60)
        
        # Show final stats
        print("\n📊 Final Battle Stats:")
        print(f"   Total Turns: {self.game_state.turn_number}")
        print(f"   Actions Taken: {len(self.game_state.battle_log.actions)}")
        
        print("\n   Player Team:")
        for c in self.game_state.get_player_characters():
            status = "Alive" if c.is_alive else "KO'd"
            print(f"     - {c.name}: {c.current_hp}/{c.max_hp} HP ({status})")
        
        print("\n   Enemy Team:")
        for c in self.game_state.get_enemy_characters():
            status = "Alive" if c.is_alive else "KO'd"
            print(f"     - {c.name}: {c.current_hp}/{c.max_hp} HP ({status})")


def run_sample_battle():
    """Run a sample interactive battle."""
    loader = get_battle_loader()
    game_state = loader.create_sample_battle()
    
    battle = InteractiveBattle(game_state)
    battle.run()


def run_battle_from_log(log_path: str):
    """Run an interactive battle from a log file."""
    loader = get_battle_loader()
    game_state = loader.load_from_battle_log(log_path)
    
    battle = InteractiveBattle(game_state)
    battle.run()


if __name__ == "__main__":
    run_sample_battle()
