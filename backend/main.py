from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from backend.routes.health import router as health_router
    from backend.routes.review_tasks import router as review_tasks_router
else:
    from .routes.health import router as health_router
    from .routes.review_tasks import router as review_tasks_router


app = FastAPI(
    title="AI PR Review Assistant API",
    description="GitHub PR review runner with real/mock LLM modes.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(review_tasks_router)
