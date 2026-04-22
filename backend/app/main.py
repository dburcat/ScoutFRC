from routers import alliances, events, matches, robot_performances, scouting_observations, sync_logs, teams, users
from fastapi import FastAPI


app = FastAPI()

app.include_router(alliances.alliance_router)
app.include_router(events.event_router)
app.include_router(matches.match_router)
app.include_router(robot_performances.robot_performance_router)
app.include_router(scouting_observations.scouting_observation_router)
app.include_router(sync_logs.sync_log_router)
app.include_router(teams.team_router)
app.include_router(users.user_router)