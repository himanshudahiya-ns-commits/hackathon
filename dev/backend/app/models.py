"""
Pydantic models (schemas) for API requests and responses.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    services: Dict[str, bool]
    timestamp: float


class BattleListResponse(BaseModel):
    battles: List[Dict[str, Any]]
    total: int


class AnalyzeRequest(BaseModel):
    battle_id: Optional[int] = Field(None, description="Battle number (1-indexed)")
    battle_path: Optional[str] = Field(None, description="Full path to battle log file")


class AnalyzeResponse(BaseModel):
    success: bool
    battle_path: str
    metrics: Dict[str, Any]
    ai_analysis: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


class TurnStateRequest(BaseModel):
    battle_id: Optional[int] = Field(None, description="Battle number to load")
    battle_path: Optional[str] = Field(None, description="Full path to battle log")
    session_id: Optional[str] = Field(None, description="Existing session ID to continue")


class SkillChoice(BaseModel):
    session_id: str
    skill_id: str
    target_id: Optional[str] = None


class AdvisorResponse(BaseModel):
    success: bool
    session_id: str
    turn_number: int
    current_actor: Dict[str, Any] | None
    is_player_turn: bool
    available_skills: List[Dict[str, Any]]
    enemies: List[Dict[str, Any]]
    allies: List[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]] = None
    battle_over: bool = False
    winner: Optional[str] = None
    health_status: Dict[str, List[Dict[str, Any]]]
    error: Optional[str] = None
    retry_count: int = 0
    last_action: Optional[Dict[str, Any]] = None


class ActionResultResponse(BaseModel):
    success: bool
    session_id: str
    action_result: Dict[str, Any]
    health_status: Dict[str, List[Dict[str, Any]]]
    battle_over: bool = False
    winner: Optional[str] = None
    error: Optional[str] = None


class AcceptRecommendationRequest(BaseModel):
    session_id: str
