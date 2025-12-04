"""
AI Advisor Module
Uses OpenAI to recommend the best skill and target for each turn.
"""
import os
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


ADVISOR_SYSTEM_PROMPT = """You are an expert combat strategist for "Looney Tunes: World of Mayhem", a turn-based mobile game.

Your job is to analyze the current battle state and recommend the BEST skill to use and which enemy to target.

Consider these factors when making recommendations:
1. **Kill Priority**: If an enemy is low HP, finish them off to reduce incoming damage
2. **Threat Assessment**: High-attack enemies or healers should be prioritized
3. **Survival**: If your character is low HP, consider defensive/healing skills
4. **Crowd Control**: Stuns/silences are valuable against dangerous enemies
5. **Buffs/Debuffs**: Attack buffs before big damage skills, debuff high-threat enemies
6. **AOE vs Single Target**: Use AOE when multiple enemies are low, single target for focus damage
7. **Cooldown Management**: Don't waste big cooldowns on nearly-dead enemies

ALWAYS respond with valid JSON in this exact format:
{
    "recommended_skill_id": "skill_id_here",
    "recommended_target_id": "target_character_id_here",
    "reason": "Brief 1-2 sentence explanation of why this is the best move"
}

If the skill is self-targeted or AOE, set recommended_target_id to null."""


class AIAdvisor:
    """AI-powered battle advisor that recommends skills and targets."""
    
    def __init__(self, api_key: str = None):
        """Initialize the AI advisor."""
        self.api_key = api_key or os.getenv("OPENAI_API")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API in .env file.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective
    
    def get_recommendation(self, turn_state: dict) -> dict:
        """
        Get AI recommendation for the current turn.
        
        Args:
            turn_state: Dictionary containing current battle state
            
        Returns:
            Dictionary with recommended_skill_id, recommended_target_id, and reason
        """
        # Build the prompt
        user_message = self._build_user_prompt(turn_state)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent recommendations
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            # Fallback to first available skill if AI fails
            print(f"AI Advisor error: {e}")
            return self._fallback_recommendation(turn_state)
    
    def _build_user_prompt(self, turn_state: dict) -> str:
        """Build the user prompt with battle state."""
        actor = turn_state.get("actor", {})
        skills = turn_state.get("actor_skills", [])
        enemies = turn_state.get("enemies", [])
        allies = turn_state.get("allies", [])
        
        prompt_parts = [
            f"## Current Turn: {turn_state.get('turn_number', 1)}",
            "",
            f"### Acting Character: {actor.get('name', 'Unknown')}",
            f"- HP: {actor.get('hp', 0)}/{actor.get('max_hp', 100)} ({actor.get('hp_percent', 100):.0f}%)",
            f"- Attack: {actor.get('attack', 0)} | Defense: {actor.get('defense', 0)} | Speed: {actor.get('speed', 0)}",
            f"- Archetype: {actor.get('archetype', 'Unknown')}",
            f"- Status: {', '.join([e['name'] for e in actor.get('status_effects', [])]) or 'None'}",
            "",
            "### Available Skills:"
        ]
        
        for skill in skills:
            if skill.get("is_available", True):
                effects = ", ".join(skill.get("effects", [])) or "none"
                prompt_parts.append(
                    f"- **{skill['name']}** (ID: {skill['skill_id']}): "
                    f"Type: {skill.get('type', 'unknown')}, Power: {skill.get('power', 100)}%, "
                    f"Effects: {effects}"
                )
                if skill.get("description"):
                    prompt_parts.append(f"  Description: {skill['description'][:150]}")
        
        prompt_parts.extend(["", "### Enemies:"])
        for enemy in enemies:
            status = ", ".join([e['name'] for e in enemy.get('status_effects', [])]) or "none"
            threat = "⚠️ HIGH THREAT" if enemy.get('attack', 0) > actor.get('attack', 0) else ""
            low_hp = "🎯 LOW HP" if enemy.get('hp_percent', 100) < 40 else ""
            prompt_parts.append(
                f"- **{enemy['name']}** (ID: {enemy['id']}): "
                f"HP: {enemy.get('hp', 0)}/{enemy.get('max_hp', 100)} ({enemy.get('hp_percent', 100):.0f}%) "
                f"| ATK: {enemy.get('attack', 0)} | Archetype: {enemy.get('archetype', 'Unknown')} "
                f"| Status: {status} {threat} {low_hp}"
            )
        
        if allies:
            prompt_parts.extend(["", "### Allies:"])
            for ally in allies:
                status = ", ".join([e['name'] for e in ally.get('status_effects', [])]) or "none"
                prompt_parts.append(
                    f"- {ally['name']}: HP: {ally.get('hp', 0)}/{ally.get('max_hp', 100)} "
                    f"({ally.get('hp_percent', 100):.0f}%) | Status: {status}"
                )
        
        prompt_parts.extend([
            "",
            "### Battle Context:",
            f"- Player characters alive: {turn_state.get('battle_context', {}).get('player_alive', 0)}",
            f"- Enemy characters alive: {turn_state.get('battle_context', {}).get('enemy_alive', 0)}",
            "",
            "What is the BEST skill to use and who should be the target? Respond in JSON format."
        ])
        
        return "\n".join(prompt_parts)
    
    def _fallback_recommendation(self, turn_state: dict) -> dict:
        """Provide a fallback recommendation if AI fails."""
        skills = turn_state.get("actor_skills", [])
        enemies = turn_state.get("enemies", [])
        
        # Pick first available skill
        skill_id = skills[0]["skill_id"] if skills else None
        
        # Pick lowest HP enemy
        target_id = None
        if enemies:
            lowest_hp_enemy = min(enemies, key=lambda e: e.get("hp_percent", 100))
            target_id = lowest_hp_enemy.get("id")
        
        return {
            "recommended_skill_id": skill_id,
            "recommended_target_id": target_id,
            "reason": "Fallback: Using first available skill on lowest HP enemy."
        }


def get_ai_advisor() -> Optional[AIAdvisor]:
    """Get or create the AI advisor singleton."""
    try:
        return AIAdvisor()
    except ValueError as e:
        print(f"Warning: {e}")
        return None
