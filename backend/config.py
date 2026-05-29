import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


GITHUB_API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_TIMEOUT_SECONDS = float(os.getenv("GITHUB_TIMEOUT_SECONDS", "15"))
GITHUB_MAX_FILES = int(os.getenv("GITHUB_MAX_FILES", "100"))
USE_MOCK_GITHUB = env_flag("USE_MOCK_GITHUB", "false")
GITHUB_ACCESS_MODE = "read_only"
GITHUB_WRITE_BACK_ENABLED = False
PLACEHOLDER_TOKENS = {"", "your_github_token_here", "github_pat_xxxxxxxxx"}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "siliconflow").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
USE_MOCK_LLM = env_flag("USE_MOCK_LLM", "false")
LLM_FALLBACK_TO_MOCK = env_flag("LLM_FALLBACK_TO_MOCK", "true")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048"))
LLM_MAX_REVIEW_FILES = int(os.getenv("LLM_MAX_REVIEW_FILES", "20"))
LLM_MAX_PATCH_CHARS = int(os.getenv("LLM_MAX_PATCH_CHARS", "8000"))
LLM_MAX_CONTEXT_CHARS = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "45000"))
LLM_USE_JSON_RESPONSE_FORMAT = env_flag("LLM_USE_JSON_RESPONSE_FORMAT", "true")
LLM_PLACEHOLDER_VALUES = {
    "",
    "your_siliconflow_api_key_here",
    "your_model_name_here",
}


def is_github_token_configured() -> bool:
    return GITHUB_TOKEN not in PLACEHOLDER_TOKENS


def is_llm_configured() -> bool:
    return LLM_API_KEY not in LLM_PLACEHOLDER_VALUES and LLM_MODEL not in {
        "",
        "your_model_name_here",
    }
