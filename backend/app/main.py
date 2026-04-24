from app.routers import alliances, events, matches, robot_performances, scouting_observations, sync_logs, teams, users, auth, admin
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# 1. Define your allowed origins
# In production, replace "*" with your actual frontend URL (e.g., https://scoutai.app)
origins = [
    "http://localhost:8000",    # Standard React port
    "http://127.0.0.1:8000",
    "http://localhost:5173"
]

# 2. Add the middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allows specific origins
    allow_credentials=True,           # Allows cookies and auth headers
    allow_methods=["*"],              # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],              # Allows all headers
)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles 404 and other manual HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Resource Error",
            "detail": exc.detail,
            "path": request.url.path
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles 422 errors (Pydantic validation failures) with type-safe parsing."""
    errors = exc.errors()
    
    if errors:
        main_error = errors[0]
        # Safely get the location list, defaulting to an empty list if not found
        loc = main_error.get('loc', [])
        # Safely get the field name (last item in loc) or default to "body"
        field_name = loc[-1] if loc else "field"
        message = main_error.get('msg', "is invalid")
        detail = f"Field '{field_name}' {message}"
    else:
        detail = "Validation failed with no specific error details."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Failed",
            "detail": detail,
            "body": exc.body 
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handles 500 errors (Unexpected crashes)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred in the ScoutAI engine.",
        },
    )

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