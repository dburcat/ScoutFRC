from routers import alliances, events, matches, robot_performances, scouting_observations, sync_logs, teams, users
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# 1. Define your allowed origins
# In production, replace "*" with your actual frontend URL (e.g., https://scoutai.app)
origins = [
    "http://localhost:8000",    # Standard React port
    "http://127.0.0.1:8000",
]

# 2. Add the middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allows specific origins
    allow_credentials=True,           # Allows cookies and auth headers
    allow_methods=["*"],              # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],              # Allows all headers
)

app.include_router(alliances.alliance_router)
app.include_router(events.event_router)
app.include_router(matches.match_router)
app.include_router(robot_performances.robot_performance_router)
app.include_router(scouting_observations.scouting_observation_router)
app.include_router(sync_logs.sync_log_router)
app.include_router(teams.team_router)
app.include_router(users.user_router)