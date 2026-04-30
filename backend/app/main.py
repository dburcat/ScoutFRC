from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import (
    video,
    alliances, events, matches, robot_performances,
    scouting_observations, sync_logs, teams, users, auth, admin, health, user_alliances, data,
)
from app.core.scheduler import start_scheduler, stop_scheduler


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Resource Error", "detail": exc.detail, "path": request.url.path},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        main_error = errors[0]
        loc = main_error.get("loc", [])
        field_name = loc[-1] if loc else "field"
        message = main_error.get("msg", "is invalid")
        detail = f"Field '{field_name}' {message}"
    else:
        detail = "Validation failed with no specific error details."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation Failed", "detail": detail, "body": exc.body},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred in the ScouterFRC engine.",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(alliances.alliance_router)
app.include_router(events.event_router)
app.include_router(matches.match_router)
app.include_router(robot_performances.robot_performance_router)
app.include_router(scouting_observations.scouting_observation_router)
app.include_router(sync_logs.sync_log_router)
app.include_router(teams.team_router)
app.include_router(users.user_router)
app.include_router(auth.auth_router)
app.include_router(admin.admin_router)
app.include_router(health.health_router)
app.include_router(user_alliances.user_alliance_router)
app.include_router(data.data_router)
app.include_router(video.video_router)