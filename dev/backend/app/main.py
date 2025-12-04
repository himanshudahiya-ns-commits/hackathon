"""
FastAPI Backend for AI Battle Tools (backend.app)
Exposes endpoints for:
1. Health check
2. Battle Analyzer (post-battle analysis)
3. Battle Advisor (turn-by-turn recommendations)
"""
import sys
import asyncio
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import wraps

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure repo root on path (../../ -> /dev)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services import (
    AnalyzerService,
    AdvisorService,
    get_analyzer_service,
    get_advisor_service,
)
from backend.app.models import (
    HealthResponse,
    BattleListResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    TurnStateRequest,
    SkillChoice,
    AdvisorResponse,
    ActionResultResponse,
    AcceptRecommendationRequest,
)

# Initialize FastAPI app
app = FastAPI(
    title="AI Battle Tools API",
    description="API for Looney Tunes: World of Mayhem battle analysis and recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Retry Decorator
# ============================================================

def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            retry_count = 0
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, dict):
                        result["retry_count"] = retry_count
                    elif hasattr(result, "retry_count"):
                        result.retry_count = retry_count
                    return result
                except Exception as e:
                    last_exception = e
                    retry_count = attempt + 1
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            raise last_exception
        return wrapper
    return decorator


# ============================================================
# Health Endpoint
# ============================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    analyzer = get_analyzer_service()
    advisor = get_advisor_service()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "analyzer": analyzer is not None,
            "advisor": advisor is not None,
            "ai_enabled": advisor.ai_advisor is not None if advisor else False,
        },
        timestamp=time.time(),
    )


# ============================================================
# Analyzer Endpoints
# ============================================================

@app.get("/analyzer/battles", response_model=BattleListResponse, tags=["Analyzer"])
async def list_battles():
    analyzer = get_analyzer_service()
    battles = analyzer.list_battles()
    return BattleListResponse(battles=battles, total=len(battles))


@app.post("/analyzer/analyze", response_model=AnalyzeResponse, tags=["Analyzer"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def analyze_battle(request: AnalyzeRequest):
    analyzer = get_analyzer_service()
    if request.battle_id:
        result = await analyzer.analyze_by_id(request.battle_id)
    elif request.battle_path:
        result = await analyzer.analyze_by_path(request.battle_path)
    else:
        raise HTTPException(status_code=400, detail="Provide either battle_id or battle_path")
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
    return AnalyzeResponse(**result)


# ============================================================
# Advisor Endpoints
# ============================================================

@app.post("/advisor/start", response_model=AdvisorResponse, tags=["Advisor"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def start_battle(request: TurnStateRequest):
    advisor = get_advisor_service()
    if request.session_id:
        result = await advisor.get_turn_state(request.session_id)
    elif request.battle_id:
        result = await advisor.start_battle_by_id(request.battle_id)
    elif request.battle_path:
        result = await advisor.start_battle_by_path(request.battle_path)
    else:
        result = await advisor.start_sample_battle()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to start battle"))
    return AdvisorResponse(**result)


@app.post("/advisor/action", response_model=ActionResultResponse, tags=["Advisor"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def apply_action(choice: SkillChoice):
    advisor = get_advisor_service()
    result = await advisor.apply_action(choice.session_id, choice.skill_id, choice.target_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to apply action"))
    return ActionResultResponse(**result)


@app.post("/advisor/accept-recommendation", response_model=ActionResultResponse, tags=["Advisor"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def accept_recommendation(request: AcceptRecommendationRequest):
    advisor = get_advisor_service()
    result = await advisor.accept_recommendation(request.session_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to accept recommendation"))
    return ActionResultResponse(**result)


@app.post("/advisor/play-turn", response_model=AdvisorResponse, tags=["Advisor"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def play_turn(choice: SkillChoice):
    advisor = get_advisor_service()
    action_result = await advisor.apply_action(choice.session_id, choice.skill_id, choice.target_id)
    if not action_result["success"]:
        raise HTTPException(status_code=500, detail=action_result.get("error", "Failed to apply action"))
    result = await advisor.advance_turn(choice.session_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to advance turn"))
    result["last_action"] = action_result.get("action_result")
    return AdvisorResponse(**result)


@app.post("/advisor/next-turn", response_model=AdvisorResponse, tags=["Advisor"])
@with_retry(max_retries=3, delay=1.0, backoff=2.0)
async def next_turn(session_id: str = Query(..., description="Battle session ID")):
    advisor = get_advisor_service()
    result = await advisor.advance_turn(session_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to advance turn"))
    return AdvisorResponse(**result)


@app.get("/advisor/sessions", tags=["Advisor"])
async def list_sessions():
    advisor = get_advisor_service()
    return {"sessions": advisor.list_sessions()}


@app.delete("/advisor/session/{session_id}", tags=["Advisor"])
async def end_session(session_id: str):
    advisor = get_advisor_service()
    success = advisor.end_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": f"Session {session_id} ended"}


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
