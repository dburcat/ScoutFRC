from db.session import get_session
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


# print("Database connection initialized")
# print("Available models:", Team, Event, Match, Alliance, RobotPerformance, ScoutingObservation)
# print("App is ready to handle requests")

# # @app.get("/models/event/{event_id}")
# # def root(event_id: int):
# #     return {"event_id": event_id}

# @app.get("/models/team/{team_id}")
# def get_team(team_id: int):
#     with get_session() as session:
#         team = session.query(Team).filter(Team.team_id == team_id).first()
#         if team:
#             return {
#                 "team_id": team.team_id,
#                 "team_number": team.team_number,
#                 "team_name": team.team_name,
#                 "school_name": team.school_name,
#                 "city": team.city,
#                 "state_prov": team.state_prov,
#                 "country": team.country,
#                 "rookie_year": team.rookie_year,
#             }
#         else:
#             return {"error": "Team not found"}, 404

# @app.get("/models/event/")
# def get_events():
#     with get_session() as session:
#         events = session.query(Event).all()
#         return [{"event_id": event.event_id, "event_name": event.name} for event in events]
    
# @app.get("/models/team/")
# def get_teams():
#     with get_session() as session:
#         teams = session.query(Team).all()
#         return [{"team_id": team.team_id, "team_number": team.team_number} for team in teams]