from fastapi import APIRouter

from ..config import (
    GITHUB_ACCESS_MODE,
    GITHUB_WRITE_BACK_ENABLED,
    LLM_MODEL,
    LLM_PROVIDER,
    USE_MOCK_GITHUB,
    USE_MOCK_LLM,
    is_github_token_configured,
    is_llm_configured,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-pr-review-assistant-api",
        "github_mode": "mock" if USE_MOCK_GITHUB else "real",
        "github_access": GITHUB_ACCESS_MODE,
        "github_write_back": "enabled" if GITHUB_WRITE_BACK_ENABLED else "disabled",
        "github_token": "configured" if is_github_token_configured() else "anonymous",
        "llm_mode": "mock" if USE_MOCK_LLM else "real",
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL or "unconfigured",
        "llm_token": "configured" if is_llm_configured() else "missing",
    }
