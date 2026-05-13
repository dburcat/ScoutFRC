"""
Seed a fake ongoing demo event for ScouterFRC.
Run with: docker compose exec backend python3 seed_demo_event.py
"""
from datetime import date, datetime, timezone
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # ── Cleanup previous run ───────────────────────────────────────────────────
    existing_event_id = db.execute(
        text("SELECT event_id FROM event WHERE tba_event_key = '2026demo_live'")
    ).scalar()
    if existing_event_id:
        db.execute(text("DELETE FROM match WHERE event_id = :eid"), {"eid": existing_event_id})
        db.execute(text("DELETE FROM event WHERE event_id = :eid"), {"eid": existing_event_id})
        db.commit()
        print(f"Cleaned up previous demo event (id={existing_event_id})")

    # ── 1. Event ───────────────────────────────────────────────────────────────
    today = date.today()
    db.execute(text("""
        INSERT INTO event (tba_event_key, name, city, state_prov, country,
                           start_date, end_date, season_year)
        VALUES ('2026demo_live',
                'Philadelphia Regional Championship',
                'Philadelphia', 'Pennsylvania', 'USA',
                :start, :end, 2026)
    """), {"start": today, "end": today})
    db.commit()

    event_id = db.execute(
        text("SELECT event_id FROM event WHERE tba_event_key = '2026demo_live'")
    ).scalar()
    print(f"Created event id={event_id}")

    # ── 2. Teams ───────────────────────────────────────────────────────────────
    teams_data = [
        (365,  "Team 365 - MOE",              "Mount Olive",      "NJ", "USA"),
        (1114, "Team 1114 - Simbotics",        "St. Catharines",   "ON", "Canada"),
        (254,  "Team 254 - Cheesy Poofs",      "San Jose",         "CA", "USA"),
        (118,  "Team 118 - Robonauts",         "Houston",          "TX", "USA"),
        (2056, "Team 2056 - OP Robotics",      "Guelph",           "ON", "Canada"),
        (1678, "Team 1678 - Citrus Circuits",  "Davis",            "CA", "USA"),
        (33,   "Team 33 - Killer Bees",        "Auburn Hills",     "MI", "USA"),
        (16,   "Team 16 - Bomb Squad",         "Hartland",         "MI", "USA"),
        (971,  "Team 971 - Spartan Robotics",  "Mountain View",    "CA", "USA"),
        (2910, "Team 2910 - Jack in the Bot",  "Bonney Lake",      "WA", "USA"),
        (3310, "Team 3310 - Black Hawk",       "Parker",           "CO", "USA"),
        (4414, "Team 4414 - HighTide",         "Aptos",            "CA", "USA"),
    ]

    team_ids = {}
    for number, name, city, state, country in teams_data:
        # Upsert — team_number has a unique constraint
        existing = db.execute(
            text("SELECT team_id FROM team WHERE team_number = :n"), {"n": number}
        ).scalar()
        if existing:
            team_ids[number] = existing
            print(f"  Team {number} already exists (id={existing})")
        else:
            db.execute(text("""
                INSERT INTO team (team_number, team_name, city, state_prov, country)
                VALUES (:n, :name, :city, :state, :country)
            """), {"n": number, "name": name, "city": city, "state": state, "country": country})
            db.commit()
            tid = db.execute(
                text("SELECT team_id FROM team WHERE team_number = :n"), {"n": number}
            ).scalar()
            team_ids[number] = tid
            print(f"  Created team {number} id={tid}")

    db.commit()

    # ── 3. Match helper ────────────────────────────────────────────────────────
    def make_match(match_num, red_teams, blue_teams,
                   red_score, blue_score,
                   red_won, blue_won,
                   status="complete"):
        """
        red_teams / blue_teams: list of 3 team_numbers
        Returns match_id
        """
        tba_key = f"2026demo_live_qm{match_num}"
        db.execute(text("""
            INSERT INTO match (event_id, tba_match_key, match_type, match_number,
                               processing_status, played_at)
            VALUES (:eid, :key, 'qualification', :num, :status, :played_at)
        """), {
            "eid": event_id,
            "key": tba_key,
            "num": match_num,
            "status": status,
            "played_at": datetime.now(timezone.utc) if status == "complete" else None,
        })
        db.commit()

        match_id = db.execute(
            text("SELECT match_id FROM match WHERE tba_match_key = :k"), {"k": tba_key}
        ).scalar()

        for color, teams, score, won in [
            ("red",  red_teams,  red_score,  red_won),
            ("blue", blue_teams, blue_score, blue_won),
        ]:
            db.execute(text("""
                INSERT INTO alliance (match_id, color, total_score, won)
                VALUES (:mid, :color, :score, :won)
            """), {"mid": match_id, "color": color, "score": score, "won": won})
            db.commit()

            alliance_id = db.execute(text("""
                SELECT alliance_id FROM alliance
                WHERE match_id = :mid AND color = :color
            """), {"mid": match_id, "color": color}).scalar()

            for pos, tn in enumerate(teams, start=1):
                db.execute(text("""
                    INSERT INTO robot_performance
                        (match_id, team_id, alliance_id, alliance_position,
                         auto_score, teleop_score, endgame_score,
                         fouls_drawn, fouls_committed, no_show, disabled)
                    VALUES (:mid, :tid, :aid, :pos,
                            :auto, :tele, :end,
                            :fd, :fc, false, false)
                """), {
                    "mid": match_id,
                    "tid": team_ids[tn],
                    "aid": alliance_id,
                    "pos": pos,
                    "auto":  score // 4,
                    "tele":  score // 2,
                    "end":   score // 8,
                    "fd": 0, "fc": 0,
                })
        db.commit()
        print(f"  Match {match_num}: red {red_teams} {red_score} vs blue {blue_teams} {blue_score}  won={'red' if red_won else 'blue'}")
        return match_id

    # ── 4. Matches ─────────────────────────────────────────────────────────────
    print("Creating matches...")

    # QM1 — red wins, team 365 on red
    make_match(1,
        red_teams=[365, 1114, 254],  blue_teams=[118, 2056, 1678],
        red_score=128,                blue_score=106,
        red_won=True,                blue_won=False)

    # QM2 — blue wins
    make_match(2,
        red_teams=[33, 16, 971],     blue_teams=[2910, 3310, 4414],
        red_score=89,                blue_score=102,
        red_won=False,               blue_won=True)

    # QM3 — red wins
    make_match(3,
        red_teams=[118, 2910, 4414], blue_teams=[365, 33, 971],
        red_score=98,                blue_score=189,
        red_won=True,                blue_won=False)

    # QM4 — blue wins
    make_match(4,
        red_teams=[254, 16, 3310],   blue_teams=[1114, 2056, 1678],
        red_score=212,                blue_score=118,
        red_won=False,               blue_won=True)

    # QM5 — red wins
    make_match(5,
        red_teams=[365, 971, 2910],  blue_teams=[254, 33, 4414],
        red_score=102,                blue_score=157,
        red_won=True,                blue_won=False)

    # QM6 — blue wins
    make_match(6,
        red_teams=[1678, 118, 16],   blue_teams=[1114, 3310, 365],
        red_score=90,                blue_score=101,
        red_won=False,               blue_won=True)

    # QM7 — red wins
    make_match(7,
        red_teams=[2056, 33, 254],   blue_teams=[971, 16, 118],
        red_score=231,                blue_score=217,
        red_won=True,                blue_won=False)

    # QM8 — blue wins
    make_match(8,
        red_teams=[4414, 1114, 365], blue_teams=[2910, 1678, 33],
        red_score=205,                blue_score=198,
        red_won=False,               blue_won=True)

    # QM9 — pending (in progress feel)
    make_match(9,
        red_teams=[971, 254, 2056],  blue_teams=[365, 16, 4414],
        red_score=0,                 blue_score=0,
        red_won=False,               blue_won=False,
        status="pending")

    # QM10 — pending
    make_match(10,
        red_teams=[3310, 118, 1678], blue_teams=[2910, 1114, 33],
        red_score=0,                 blue_score=0,
        red_won=False,               blue_won=False,
        status="pending")

    print(f"\n✅ Done! Event '{event_id}' seeded with 12 teams and 10 qualification matches.")
    print(f"   Team 365 is on the RED alliance in QM1 (red wins 78–55).")

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    raise
finally:
    db.close()