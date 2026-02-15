from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import dashboard, demo, health, intake, interviews, pain_points, report, respondents, scores
from app.config import get_settings
from app.db import init_db

settings = get_settings()
app = FastAPI(title=settings.app_name)
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.app_name, "status": "running"}


app.include_router(health.router)
app.include_router(intake.router)
app.include_router(respondents.router)
app.include_router(interviews.router)
app.include_router(pain_points.router)
app.include_router(scores.router)
app.include_router(dashboard.router)
app.include_router(report.router)
app.include_router(demo.router)
