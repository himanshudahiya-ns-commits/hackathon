"""
LLM Analyzer Module
Builds prompts and calls OpenAI API to analyze battle results.
"""
import os
import json
from dataclasses import asdict
from typing import Optional, List
from openai import OpenAI
from dotenv import load_dotenv

from .metrics import BattleMetrics
from .db_helper import get_db_helper, get_battle_character_context, CharacterInfo
from .csv_helper import get_csv_loader, get_character_csv_info, get_skill_csv_info


# Load environment variables
load_dotenv()


SYSTEM_PROMPT = """You are an expert game combat analyst for "Looney Tunes: World of Mayhem", a turn-based mobile game. 
Your job is to analyze battle replays and explain to players why they won or lost (or almost lost) a battle.

You have access to detailed character database information including:
- Character archetypes (Attacker, Defender, Support, etc.)
- Rarity and battle tier
- Base stats and how they compare to average
- Character themes and families (which affect synergies)

When analyzing a battle, provide:
1. A brief summary of what happened (2-3 sentences)
2. Key reasons for the outcome (3-5 bullet points) - use character database info to explain WHY certain characters performed well/poorly
3. Actionable suggestions for improvement (2-3 bullet points)

Be friendly, clear, and specific. Reference actual character names, stats, and events from the battle.
Focus on actionable insights like:
- Which stats to improve (attack, defense, speed, health)
- Which enemy to focus first based on their archetype/threat level
- Team composition suggestions (need healer, tank, etc.) based on archetypes
- Turn order and speed advantages
- Buff/debuff management
- Synergy opportunities based on character themes/families

Keep your response concise but informative. Use simple language that any player can understand."""


def get_character_db_info(character_name: str) -> dict:
    """Fetch character info from database and CSV files."""
    result = {}
    
    # Try database first
    db = get_db_helper()
    if db:
        char_info = db.get_character(character_name)
        if char_info:
            result = {
                "display_name": char_info.name,
                "description": char_info.description,
                "rarity": char_info.rarity,
                "archetype": char_info.archetype,
                "battle_tier": char_info.battle_tier,
                "region": char_info.region,
                "theme": char_info.theme,
                "family": char_info.family,
                "race": char_info.race,
                "base_stats": {
                    "attack": char_info.attack,
                    "defense": char_info.defense,
                    "health": char_info.health,
                    "speed": char_info.speed
                },
                "pct_vs_average": char_info.pct_to_avg
            }
    
    # Enrich with CSV data (has more detailed stats and skills)
    csv_info = get_character_csv_info(character_name)
    if csv_info:
        # Merge CSV data, preferring CSV for stats if available
        if not result:
            result = csv_info
        else:
            # Update with CSV data where it has better info
            if csv_info.get("base_stats", {}).get("attack", 0) > 0:
                result["base_stats"] = csv_info["base_stats"]
            if csv_info.get("relative_stats"):
                result["relative_stats"] = csv_info["relative_stats"]
            if csv_info.get("total_power"):
                result["total_power"] = csv_info["total_power"]
            if csv_info.get("skills"):
                result["skills"] = csv_info["skills"]
            # Fill in missing fields
            for key in ["display_name", "rarity", "archetype", "theme", "region", "family", "race"]:
                if not result.get(key) and csv_info.get(key):
                    result[key] = csv_info[key]
    
    return result


def get_skill_info(skill_id: str) -> dict:
    """Fetch skill info from CSV files."""
    return get_skill_csv_info(skill_id)


def build_battle_summary(metrics: BattleMetrics, include_db_info: bool = True) -> dict:
    """Build a clean JSON summary for the LLM."""
    
    # Player team summary
    player_team = {
        "characters": [
            {
                "name": c.name,
                "archetype": c.archetype,
                "level": c.level,
                "stats": {
                    "health": c.starting_health,
                    "attack": c.starting_attack,
                    "defense": c.starting_defense,
                    "speed": c.starting_speed
                },
                "performance": {
                    "damage_dealt": c.total_damage_dealt,
                    "damage_taken": c.total_damage_taken,
                    "turns_taken": c.turns_taken,
                    "was_ko": c.was_ko,
                    "ko_turn": c.ko_turn,
                    "final_health_percent": round(c.final_health_percent, 1)
                },
                "db_info": get_character_db_info(c.name) if include_db_info else {}
            }
            for c in metrics.player_characters
        ],
        "totals": {
            "avg_attack": round(metrics.player_team.avg_attack, 1),
            "avg_defense": round(metrics.player_team.avg_defense, 1),
            "avg_speed": round(metrics.player_team.avg_speed, 1),
            "avg_health": round(metrics.player_team.avg_health, 1),
            "total_damage": metrics.player_team.total_damage_dealt,
            "characters_alive": metrics.player_team.characters_alive,
            "had_first_turn": metrics.player_team.first_turn
        }
    }
    
    # Enemy team summary
    enemy_team = {
        "characters": [
            {
                "name": c.name,
                "archetype": c.archetype,
                "level": c.level,
                "stats": {
                    "health": c.starting_health,
                    "attack": c.starting_attack,
                    "defense": c.starting_defense,
                    "speed": c.starting_speed
                },
                "performance": {
                    "damage_dealt": c.total_damage_dealt,
                    "damage_taken": c.total_damage_taken,
                    "turns_taken": c.turns_taken,
                    "was_ko": c.was_ko,
                    "ko_turn": c.ko_turn,
                    "final_health_percent": round(c.final_health_percent, 1)
                },
                "db_info": get_character_db_info(c.name) if include_db_info else {}
            }
            for c in metrics.enemy_characters
        ],
        "totals": {
            "avg_attack": round(metrics.enemy_team.avg_attack, 1),
            "avg_defense": round(metrics.enemy_team.avg_defense, 1),
            "avg_speed": round(metrics.enemy_team.avg_speed, 1),
            "avg_health": round(metrics.enemy_team.avg_health, 1),
            "total_damage": metrics.enemy_team.total_damage_dealt,
            "characters_alive": metrics.enemy_team.characters_alive,
            "had_first_turn": metrics.enemy_team.first_turn
        }
    }
    
    # Build summary
    summary = {
        "result": metrics.result,
        "total_turns": metrics.total_turns,
        "stars": metrics.stars,
        "player_team": player_team,
        "enemy_team": enemy_team,
        "stat_advantages": {
            "speed": metrics.speed_advantage,
            "attack": metrics.attack_advantage,
            "defense": metrics.defense_advantage,
            "health": metrics.health_advantage
        },
        "key_events": {
            "first_ko": metrics.first_ko,
            "biggest_hit": metrics.biggest_hit,
            "turn_order": metrics.turn_order
        },
        "key_moments": metrics.key_moments
    }
    
    return summary


def build_user_prompt(summary: dict) -> str:
    """Build the user prompt with battle data."""
    result_text = "WON" if summary["result"] == "WIN" else "LOST"
    
    prompt = f"""Analyze this battle where the player {result_text}.

## Battle Summary
{json.dumps(summary, indent=2)}

Please provide:
1. **Battle Summary**: What happened in this battle? (2-3 sentences)
2. **Key Factors**: Why did the player {result_text.lower()}? (3-5 bullet points)
3. **Suggestions**: What should the player do differently next time? (2-3 actionable tips)

Focus on specific characters, stats, and events from this battle."""
    
    return prompt


class BattleAnalyzer:
    """Analyzes battles using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """Initialize the analyzer with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API in .env file.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def analyze(self, metrics: BattleMetrics) -> str:
        """Analyze battle metrics and return explanation."""
        # Build the summary
        summary = build_battle_summary(metrics)
        
        # Build prompts
        user_prompt = build_user_prompt(summary)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error analyzing battle: {str(e)}"
    
    def analyze_with_details(self, metrics: BattleMetrics) -> dict:
        """Analyze and return both the analysis and the raw data."""
        summary = build_battle_summary(metrics)
        analysis = self.analyze(metrics)
        
        return {
            "analysis": analysis,
            "summary": summary,
            "metrics": {
                "result": metrics.result,
                "total_turns": metrics.total_turns,
                "stars": metrics.stars,
                "player_damage": metrics.player_team.total_damage_dealt,
                "enemy_damage": metrics.enemy_team.total_damage_dealt,
                "player_alive": metrics.player_team.characters_alive,
                "enemy_alive": metrics.enemy_team.characters_alive
            }
        }


def analyze_battle(metrics: BattleMetrics, api_key: Optional[str] = None) -> str:
    """Convenience function to analyze a battle."""
    analyzer = BattleAnalyzer(api_key=api_key)
    return analyzer.analyze(metrics)
