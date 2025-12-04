"""
Backend Service layer for API endpoints.
Handles business logic and integrates with battle_advisor and combat_analyzer.
"""
import os
import sys
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Ensure repo root on path (../../ -> /dev)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import battle tools
from battle_advisor.game_state import GameState, Team
from battle_advisor.battle_loader import BattleLoader, get_battle_loader
from battle_advisor.ai_advisor import AIAdvisor, get_ai_advisor
from combat_analyzer.battle_parser import parse_battle_log
from combat_analyzer.metrics import compute_battle_metrics
from combat_analyzer.llm_analyzer import analyze_battle


# ============================================================
# Battle Log Discovery
# ============================================================

def find_battle_logs(base_dir: str = None) -> List[Dict[str, str]]:
    """Find all battle log files with metadata."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent.parent / "sourse"
    else:
        base_dir = Path(base_dir)
    
    logs = []
    if base_dir.exists():
        for log_file in sorted(base_dir.rglob("client_battle_log_*.txt")):
            logs.append({
                "id": len(logs) + 1,
                "path": str(log_file),
                "folder": log_file.parent.name,
                "filename": log_file.name
            })
    
    return logs


# ============================================================
# Analyzer Service
# ============================================================

class AnalyzerService:
    """Service for battle analysis."""
    
    def __init__(self):
        self.battle_logs = find_battle_logs()
    
    def list_battles(self) -> List[Dict[str, str]]:
        return self.battle_logs
    
    async def analyze_by_id(self, battle_id: int) -> Dict[str, Any]:
        if battle_id < 1 or battle_id > len(self.battle_logs):
            return {"success": False, "error": f"Invalid battle ID. Choose 1-{len(self.battle_logs)}"}
        battle_path = self.battle_logs[battle_id - 1]["path"]
        return await self.analyze_by_path(battle_path)
    
    async def analyze_by_path(self, battle_path: str) -> Dict[str, Any]:
        if not os.path.exists(battle_path):
            return {"success": False, "error": f"Battle log not found: {battle_path}"}
        try:
            parsed = parse_battle_log(battle_path)
            metrics = compute_battle_metrics(parsed)
            loop = asyncio.get_event_loop()
            ai_analysis = await loop.run_in_executor(None, analyze_battle, metrics)
            return {
                "success": True,
                "battle_path": battle_path,
                "metrics": self._serialize_metrics(metrics),
                "ai_analysis": ai_analysis,
                "retry_count": 0,
            }
        except Exception as e:
            return {"success": False, "battle_path": battle_path, "metrics": {}, "error": str(e), "retry_count": 0}
    
    def _serialize_metrics(self, metrics) -> Dict[str, Any]:
        return {
            "result": metrics.result,
            "winner_team": metrics.winner_team,
            "total_turns": metrics.total_turns,
            "stars": metrics.stars,
            "player_team": {
                "character_count": metrics.player_team.character_count,
                "avg_attack": metrics.player_team.avg_attack,
                "avg_defense": metrics.player_team.avg_defense,
                "avg_speed": metrics.player_team.avg_speed,
                "total_damage_dealt": metrics.player_team.total_damage_dealt,
                "characters_alive": metrics.player_team.characters_alive,
                "archetypes": metrics.player_team.archetypes,
            },
            "enemy_team": {
                "character_count": metrics.enemy_team.character_count,
                "avg_attack": metrics.enemy_team.avg_attack,
                "avg_defense": metrics.enemy_team.avg_defense,
                "avg_speed": metrics.enemy_team.avg_speed,
                "total_damage_dealt": metrics.enemy_team.total_damage_dealt,
                "characters_alive": metrics.enemy_team.characters_alive,
                "archetypes": metrics.enemy_team.archetypes,
            },
            "stat_advantages": {
                "speed": metrics.speed_advantage,
                "attack": metrics.attack_advantage,
                "defense": metrics.defense_advantage,
                "health": metrics.health_advantage,
            },
            "first_ko": metrics.first_ko,
            "biggest_hit": metrics.biggest_hit,
            "key_moments": metrics.key_moments,
        }


# ============================================================
# Advisor Service
# ============================================================

class AdvisorService:
    def __init__(self):
        self.battle_loader = get_battle_loader()
        self.ai_advisor = get_ai_advisor()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.battle_logs = find_battle_logs()
    
    def _create_session(self, game_state: GameState) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "game_state": game_state,
            "created_at": datetime.now(),
            "turn_history": [],
        }
        return session_id
    
    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"session_id": sid, "created_at": data["created_at"].isoformat(), "turn_number": data["game_state"].turn_number}
            for sid, data in self.sessions.items()
        ]
    
    def end_session(self, session_id: str) -> bool:
        return bool(self.sessions.pop(session_id, None))
    
    async def start_sample_battle(self) -> Dict[str, Any]:
        game_state = self.battle_loader.create_sample_battle()
        session_id = self._create_session(game_state)
        return await self.get_turn_state(session_id)
    
    async def start_battle_by_id(self, battle_id: int) -> Dict[str, Any]:
        if battle_id < 1 or battle_id > len(self.battle_logs):
            return {"success": False, "error": f"Invalid battle ID. Choose 1-{len(self.battle_logs)}"}
        battle_path = self.battle_logs[battle_id - 1]["path"]
        return await self.start_battle_by_path(battle_path)
    
    async def start_battle_by_path(self, battle_path: str) -> Dict[str, Any]:
        if not os.path.exists(battle_path):
            return {"success": False, "error": f"Battle log not found: {battle_path}"}
        try:
            game_state = self.battle_loader.load_from_battle_log(battle_path)
            session_id = self._create_session(game_state)
            return await self.get_turn_state(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_turn_state(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session not found: {session_id}"}
        game_state = session["game_state"]
        actor = game_state.current_actor
        if not actor:
            return self._build_battle_over_response(session_id, game_state)
        is_player_turn = actor.team == Team.PLAYER
        response = {
            "success": True,
            "session_id": session_id,
            "turn_number": game_state.turn_number,
            "current_actor": self._serialize_character(actor),
            "is_player_turn": is_player_turn,
            "available_skills": [self._serialize_skill(s) for s in actor.get_available_skills()],
            "enemies": [self._serialize_character(c) for c in game_state.get_enemies_of(actor)],
            "allies": [self._serialize_character(c) for c in game_state.get_allies_of(actor)],
            "health_status": self._get_health_status(game_state),
            "battle_over": game_state.is_over(),
            "winner": game_state.winner.value if game_state.winner else None,
            "recommendation": None,
            "retry_count": 0,
        }
        if is_player_turn and self.ai_advisor and not game_state.is_over():
            try:
                turn_state = game_state.build_turn_state()
                loop = asyncio.get_event_loop()
                recommendation = await loop.run_in_executor(None, self.ai_advisor.get_recommendation, turn_state)
                response["recommendation"] = recommendation
            except Exception as e:
                print(f"AI recommendation error: {e}")
        return response
    
    async def apply_action(self, session_id: str, skill_id: str, target_id: Optional[str]) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session not found: {session_id}"}
        game_state = session["game_state"]
        actor = game_state.current_actor
        if not actor:
            return {"success": False, "error": "No current actor"}
        skill = next((s for s in actor.skills if s.skill_id == skill_id), None)
        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_id}"}
        target = game_state.find_character(target_id) if target_id else None
        try:
            action = game_state.apply_skill(actor, skill, target)
            return {
                "success": True,
                "session_id": session_id,
                "action_result": {
                    "actor": actor.name,
                    "skill": skill.name,
                    "target": target.name if target else None,
                    "damage_dealt": action.damage_dealt,
                    "healing_done": action.healing_done,
                    "effects_applied": action.effects_applied,
                    "target_ko": target and not target.is_alive if target else False,
                },
                "health_status": self._get_health_status(game_state),
                "battle_over": game_state.is_over(),
                "winner": game_state.winner.value if game_state.winner else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def accept_recommendation(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session not found: {session_id}"}
        game_state = session["game_state"]
        actor = game_state.current_actor
        if not actor or actor.team != Team.PLAYER:
            return {"success": False, "error": "Not a player turn"}
        if not self.ai_advisor:
            return {"success": False, "error": "AI advisor not available"}
        try:
            turn_state = game_state.build_turn_state()
            recommendation = self.ai_advisor.get_recommendation(turn_state)
            skill_id = recommendation.get("recommended_skill_id")
            target_id = recommendation.get("recommended_target_id")
            result = await self.apply_action(session_id, skill_id, target_id)
            if result["success"]:
                result["recommendation_used"] = recommendation
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def advance_turn(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session not found: {session_id}"}
        game_state = session["game_state"]
        game_state.advance_turn()
        while not game_state.is_over():
            actor = game_state.current_actor
            if not actor:
                break
            if actor.team == Team.PLAYER:
                break
            if not actor.is_stunned:
                available_skills = actor.get_available_skills()
                if available_skills:
                    skill = available_skills[0]
                    targets = game_state.get_valid_targets(actor, skill)
                    if targets:
                        target = min(targets, key=lambda t: t.hp_percent)
                        game_state.apply_skill(actor, skill, target)
            game_state.advance_turn()
        return await self.get_turn_state(session_id)
    
    def _build_battle_over_response(self, session_id: str, game_state: GameState) -> Dict[str, Any]:
        return {
            "success": True,
            "session_id": session_id,
            "turn_number": game_state.turn_number,
            "current_actor": None,
            "is_player_turn": False,
            "available_skills": [],
            "enemies": [],
            "allies": [],
            "health_status": self._get_health_status(game_state),
            "battle_over": True,
            "winner": game_state.winner.value if game_state.winner else None,
            "recommendation": None,
            "retry_count": 0,
        }
    
    def _serialize_character(self, char) -> Dict[str, Any]:
        return {
            "id": char.character_id,
            "name": char.name,
            "hp": char.current_hp,
            "max_hp": char.max_hp,
            "hp_percent": char.hp_percent,
            "attack": char.attack,
            "defense": char.defense,
            "speed": char.speed,
            "archetype": char.archetype,
            "is_alive": char.is_alive,
            "is_stunned": char.is_stunned,
            "status_effects": [{"name": e.name, "duration": e.duration} for e in char.status_effects],
        }
    
    def _serialize_skill(self, skill) -> Dict[str, Any]:
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "type": skill.skill_type.value,
            "power": skill.power,
            "cooldown": skill.cooldown,
            "max_cooldown": skill.max_cooldown,
            "description": skill.description,
            "effects": skill.effects,
            "is_available": skill.cooldown == 0 and not skill.is_passive,
        }
    
    def _get_health_status(self, game_state: GameState) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "player_team": [
                {"name": c.name, "hp": c.current_hp, "max_hp": c.max_hp, "hp_percent": c.hp_percent, "is_alive": c.is_alive}
                for c in game_state.get_player_characters()
            ],
            "enemy_team": [
                {"name": c.name, "hp": c.current_hp, "max_hp": c.max_hp, "hp_percent": c.hp_percent, "is_alive": c.is_alive}
                for c in game_state.get_enemy_characters()
            ],
        }


# ============================================================
# Service Singletons
# ============================================================

_analyzer_service: Optional[AnalyzerService] = None
_advisor_service: Optional[AdvisorService] = None


def get_analyzer_service() -> AnalyzerService:
    global _analyzer_service
    if _analyzer_service is None:
        _analyzer_service = AnalyzerService()
    return _analyzer_service


def get_advisor_service() -> AdvisorService:
    global _advisor_service
    if _advisor_service is None:
        _advisor_service = AdvisorService()
    return _advisor_service
