from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / "countdowner.sqlite3"
ISO_FORMAT = "%Y-%m-%dT%H:%M"


NEXT_STEPS = {
    "fitness": "Log one workout, walk, stretch, or meal choice that moves the body in the right direction.",
    "learning": "Pick one small lesson, page, or practice block and finish it before adding more scope.",
    "career": "Choose the next concrete action and do it before the day starts pulling at you.",
    "wellbeing": "Protect one quiet action today: rest, journaling, a walk, or a conversation you need.",
    "finance": "Record one number, reduce one avoidable spend, or move one amount toward the target.",
    "default": "Choose the smallest useful action and make the goal easier to return to tomorrow.",
}


TONE_LINES = {
    "gentle": {
        "not_started": "No drama needed. Begin with the smallest version so this goal feels approachable.",
        "early": "You have started, and that matters. Keep the next step light enough to repeat.",
        "steady": "You are building trust with yourself. Stay with the rhythm that is already working.",
        "behind": "You are behind, but this is still recoverable. Shrink the next step and keep the promise alive.",
        "almost": "You are close. Finish cleanly, without turning the final stretch into pressure.",
        "overdue": "The date slipped, but the goal still has useful information. Adjust it kindly and continue.",
        "complete": "You followed through. Pause long enough to let the win land.",
    },
    "direct": {
        "not_started": "Start today. One visible action is better than another perfect plan.",
        "early": "Momentum is fragile right now. Protect it with one clear action.",
        "steady": "You are on course. Keep executing and do not renegotiate the basics.",
        "behind": "You are slipping. Cut the scope, act now, and make the next update real.",
        "almost": "This is the finish line zone. Close it out.",
        "overdue": "This missed the date. Reset the deadline or reduce the scope, then move.",
        "complete": "Done. That is the standard to build from next.",
    },
    "practical": {
        "not_started": "Set up the first tiny action now so the next check-in has progress to show.",
        "early": "Turn this into a repeatable routine: same cue, same time, same next step.",
        "steady": "Keep the system simple. Repeat what is working and update the tracker after each action.",
        "behind": "Recover with a smaller target for today, then decide whether the timeline needs adjusting.",
        "almost": "List what remains, remove anything optional, and finish the essential part first.",
        "overdue": "Review what blocked progress, set a new realistic date, and preserve any progress made.",
        "complete": "Capture what worked before starting the next goal.",
    },
    "competitive": {
        "not_started": "Put a first mark on the board today. Future you needs something to beat.",
        "early": "You are in the opening round. Stack one more proof point.",
        "steady": "Good pace. Keep the streak alive and make the scoreboard move.",
        "behind": "The gap is visible. Win the next hour instead of debating the whole goal.",
        "almost": "You are within striking distance. Finish stronger than you started.",
        "overdue": "The clock won this round. Take the lesson and set up the rematch.",
        "complete": "Win recorded. Raise the bar thoughtfully.",
    },
    "reflective": {
        "not_started": "Ask what would make starting feel safe and simple, then do only that.",
        "early": "Notice what helped you begin. That clue is part of the goal now.",
        "steady": "Your pattern is becoming visible. Keep the parts that support your energy.",
        "behind": "Look for the real friction, not the self-criticism. One adjustment can restart movement.",
        "almost": "Before rushing, notice the version of you that brought this this far.",
        "overdue": "The missed date is feedback. What needs to change: scope, support, timing, or desire?",
        "complete": "This win says something about what works for you. Keep that evidence.",
    },
}


REWARD_IDEAS = {
    "movie": {
        "fitness": "A feel-good sports movie night with your favorite snack.",
        "learning": "A thoughtful documentary or limited series related to what you studied.",
        "default": "A movie or series night chosen purely for comfort and joy.",
    },
    "date": {
        "fitness": "An active date: a scenic walk, bowling, or a dance class together.",
        "wellbeing": "A slow dinner date with phones away and no productivity talk.",
        "default": "A planned date with your partner where the goal gets a proper toast.",
    },
    "shopping": {
        "career": "A useful upgrade for your workspace or wardrobe.",
        "fitness": "New workout gear that makes the next goal feel inviting.",
        "default": "A shopping trip with a clear budget and zero guilt.",
    },
    "purchase": {
        "learning": "A book, course, or tool that supports the next chapter.",
        "fitness": "A tracker, bottle, mat, or gear item you had your eye on.",
        "default": "One wishlist item that feels earned and intentional.",
    },
    "trip": {
        "wellbeing": "A short recharge trip or day outing somewhere peaceful.",
        "default": "A mini trip or experience that marks the win properly.",
    },
}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                favorite_authors TEXT NOT NULL DEFAULT '',
                motivation_style TEXT NOT NULL DEFAULT 'practical',
                reward_preferences TEXT NOT NULL DEFAULT 'movie',
                wishlist TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                recurrence TEXT NOT NULL,
                due_at TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 3,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                completed_at TEXT,
                created_at TEXT NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS trackers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                metric TEXT NOT NULL,
                target REAL NOT NULL,
                unit TEXT NOT NULL,
                current REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(goal_id) REFERENCES goals(id)
            );

            CREATE TABLE IF NOT EXISTS shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                shared_with_email TEXT NOT NULL,
                accepted_user_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES goals(id),
                FOREIGN KEY(owner_id) REFERENCES users(id),
                FOREIGN KEY(accepted_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cheers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES goals(id),
                FOREIGN KEY(from_user_id) REFERENCES users(id)
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "motivation_style" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN motivation_style TEXT NOT NULL DEFAULT 'practical'")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_due(value: str) -> datetime:
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def json_response(handler: SimpleHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def cookie_token(handler: SimpleHTTPRequestHandler) -> Optional[str]:
    raw = handler.headers.get("Cookie", "")
    for chunk in raw.split(";"):
        name, _, value = chunk.strip().partition("=")
        if name == "countdowner_session":
            return value
    return None


def current_user(handler: SimpleHTTPRequestHandler) -> Optional[sqlite3.Row]:
    token = cookie_token(handler)
    if not token:
        return None
    with db() as conn:
        return conn.execute(
            """
            SELECT users.* FROM users
            JOIN sessions ON sessions.user_id = users.id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()


def require_user(handler: SimpleHTTPRequestHandler) -> Optional[sqlite3.Row]:
    user = current_user(handler)
    if not user:
        json_response(handler, {"error": "Please create or open an account first."}, HTTPStatus.UNAUTHORIZED)
        return None
    return user


def goal_progress(goal: Dict[str, Any], trackers: List[Dict[str, Any]]) -> float:
    if goal["status"] == "complete":
        return 1.0
    if trackers:
        tracker = trackers[0]
        if tracker["target"] > 0:
            return max(0.0, min(1.0, float(tracker["current"]) / float(tracker["target"])))

    created = datetime.fromisoformat(goal["created_at"])
    due = parse_due(goal["due_at"])
    total = max(1.0, (due - created).total_seconds())
    elapsed = max(0.0, (datetime.now(timezone.utc) - created).total_seconds())
    return max(0.0, min(1.0, elapsed / total))


def motivation_stage(goal: Dict[str, Any], progress: float) -> str:
    if goal["status"] == "complete":
        return "complete"
    seconds_remaining = goal["seconds_remaining"]
    if seconds_remaining < 0:
        return "overdue"
    if progress <= 0.01:
        return "not_started"
    if progress >= 0.85:
        return "almost"

    created = datetime.fromisoformat(goal["created_at"])
    due = parse_due(goal["due_at"])
    total = max(1.0, (due - created).total_seconds())
    elapsed_ratio = max(0.0, min(1.0, (datetime.now(timezone.utc) - created).total_seconds() / total))
    if progress + 0.15 < elapsed_ratio or (seconds_remaining < 86400 and progress < 0.7):
        return "behind"
    if progress < 0.25:
        return "early"
    return "steady"


def motivation_for(goal: Dict[str, Any], user: sqlite3.Row, trackers: List[Dict[str, Any]]) -> Dict[str, str]:
    style = user["motivation_style"] if "motivation_style" in user.keys() else "practical"
    if style not in TONE_LINES:
        style = "practical"
    progress = goal_progress(goal, trackers)
    stage = motivation_stage(goal, progress)
    opener = TONE_LINES[style][stage]
    next_step = NEXT_STEPS.get(goal["category"], NEXT_STEPS["default"])
    priority_note = " Because this is high priority, make it one of the first things you touch today." if goal["priority"] >= 4 and stage not in {"complete", "overdue"} else ""
    return {
        "text": f"{opener} {next_step}{priority_note}",
        "label": f"{style.title()} coaching - {stage.replace('_', ' ')} - {round(progress * 100)}%",
    }


def reward_for(goal: Dict[str, Any], user: sqlite3.Row) -> Dict[str, str]:
    preferences = [item.strip() for item in user["reward_preferences"].split(",") if item.strip()]
    reward_type = preferences[(goal["priority"] - 1) % len(preferences)] if preferences else "movie"
    ideas = REWARD_IDEAS.get(reward_type, REWARD_IDEAS["movie"])
    base = ideas.get(goal["category"], ideas.get("default", "A reward that feels personal and earned."))
    wishlist = user["wishlist"].strip()

    completed_at = goal.get("completed_at")
    bonus = ""
    if completed_at:
        due = parse_due(goal["due_at"])
        completed = datetime.fromisoformat(completed_at)
        if completed <= due:
            bonus = " You finished on time, so make it a proper celebration."
        if goal["priority"] >= 4 and completed <= due:
            bonus += " Since this was high priority, choose the richer version of the reward."
    if wishlist and reward_type in {"purchase", "shopping"}:
        base += f" Consider this from your wishlist: {wishlist}."
    return {"type": reward_type, "idea": (base + bonus).strip()}


def enrich_goal(goal: sqlite3.Row, user: sqlite3.Row) -> Dict[str, Any]:
    result = row_to_dict(goal)
    due = parse_due(result["due_at"])
    remaining = due - datetime.now(timezone.utc)
    result["seconds_remaining"] = int(remaining.total_seconds())
    with db() as conn:
        result["trackers"] = [
            row_to_dict(row)
            for row in conn.execute("SELECT * FROM trackers WHERE goal_id = ? ORDER BY id", (goal["id"],))
        ]
        result["cheers"] = [
            row_to_dict(row)
            for row in conn.execute(
                """
                SELECT cheers.*, users.name AS from_name
                FROM cheers JOIN users ON users.id = cheers.from_user_id
                WHERE goal_id = ? ORDER BY cheers.created_at DESC LIMIT 8
                """,
                (goal["id"],),
            )
        ]
        result["shares"] = [
            row_to_dict(row)
            for row in conn.execute("SELECT * FROM shares WHERE goal_id = ? ORDER BY created_at DESC", (goal["id"],))
        ]
    result["motivation"] = motivation_for(result, user, result["trackers"])
    result["reward"] = reward_for(result, user)
    return result


def get_goal_for_user(goal_id: int, user_id: int) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute(
            """
            SELECT goals.* FROM goals
            LEFT JOIN shares ON shares.goal_id = goals.id
            WHERE goals.id = ?
              AND (goals.user_id = ? OR shares.accepted_user_id = ?)
            """,
            (goal_id, user_id, user_id),
        ).fetchone()


class CountdownerHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(ROOT / "static" / "index.html")
        if parsed.path.startswith("/static/"):
            return str(ROOT / parsed.path.lstrip("/"))
        return str(ROOT / "static" / parsed.path.lstrip("/"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return super().do_GET()

        user = current_user(self)
        if parsed.path == "/api/me":
            json_response(self, {"user": row_to_dict(user) if user else None})
            return

        if not user:
            json_response(self, {"error": "Please create or open an account first."}, HTTPStatus.UNAUTHORIZED)
            return

        if parsed.path == "/api/goals":
            with db() as conn:
                rows = conn.execute(
                    """
                    SELECT DISTINCT goals.* FROM goals
                    LEFT JOIN shares ON shares.goal_id = goals.id
                    WHERE goals.user_id = ? OR shares.accepted_user_id = ?
                    ORDER BY status ASC, due_at ASC
                    """,
                    (user["id"], user["id"]),
                ).fetchall()
            json_response(self, {"goals": [enrich_goal(row, user) for row in rows]})
            return

        if parsed.path == "/api/invites":
            with db() as conn:
                rows = conn.execute(
                    """
                    SELECT shares.*, goals.title, goals.category, users.name AS owner_name
                    FROM shares
                    JOIN goals ON goals.id = shares.goal_id
                    JOIN users ON users.id = shares.owner_id
                    WHERE shares.shared_with_email = ? AND shares.accepted_user_id IS NULL
                    ORDER BY shares.created_at DESC
                    """,
                    (user["email"],),
                ).fetchall()
            json_response(self, {"invites": [row_to_dict(row) for row in rows]})
            return

        json_response(self, {"error": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            json_response(self, {"error": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)
            return

        data = read_json(self)
        if parsed.path == "/api/account":
            self.create_or_open_account(data)
            return

        user = require_user(self)
        if not user:
            return

        routes = {
            "/api/logout": self.logout,
            "/api/goals": lambda payload, actor: self.create_goal(payload, actor),
            "/api/goals/complete": lambda payload, actor: self.complete_goal(payload, actor),
            "/api/trackers/update": lambda payload, actor: self.update_tracker(payload, actor),
            "/api/share": lambda payload, actor: self.share_goal(payload, actor),
            "/api/invites/accept": lambda payload, actor: self.accept_invite(payload, actor),
            "/api/cheer": lambda payload, actor: self.add_cheer(payload, actor),
        }
        action = routes.get(parsed.path)
        if not action:
            json_response(self, {"error": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)
            return
        action(data, user)

    def create_or_open_account(self, data: Dict[str, Any]) -> None:
        email = data.get("email", "").strip().lower()
        name = data.get("name", "").strip()
        if not email or not name:
            json_response(self, {"error": "Name and email are required."}, HTTPStatus.BAD_REQUEST)
            return

        with db() as conn:
            existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, motivation_style = ?, reward_preferences = ?, wishlist = ?
                    WHERE email = ?
                    """,
                    (
                        name,
                        data.get("motivation_style", "practical"),
                        ",".join(data.get("reward_preferences", ["movie"])),
                        data.get("wishlist", "").strip(),
                        email,
                    ),
                )
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            else:
                conn.execute(
                    """
                    INSERT INTO users (name, email, motivation_style, reward_preferences, wishlist, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        data.get("motivation_style", "practical"),
                        ",".join(data.get("reward_preferences", ["movie"])),
                        data.get("wishlist", "").strip(),
                        now_iso(),
                    ),
                )
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            token = secrets.token_urlsafe(32)
            conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], now_iso()))

        body = json.dumps({"user": row_to_dict(user)}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", f"countdowner_session={token}; Path=/; SameSite=Lax")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def logout(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        token = cookie_token(self)
        if token:
            with db() as conn:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", "countdowner_session=; Path=/; Max-Age=0")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def create_goal(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        title = data.get("title", "").strip()
        due_at = data.get("due_at", "").strip()
        if not title or not due_at:
            json_response(self, {"error": "Goal name and due date are required."}, HTTPStatus.BAD_REQUEST)
            return

        category = data.get("category", "default")
        tracker = data.get("tracker") or {}
        with db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO goals
                (user_id, title, category, recurrence, due_at, priority, notes, created_at, invite_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    title,
                    category,
                    data.get("recurrence", "one-time"),
                    due_at,
                    int(data.get("priority", 3)),
                    data.get("notes", "").strip(),
                    now_iso(),
                    secrets.token_urlsafe(8),
                ),
            )
            goal_id = cursor.lastrowid
            if tracker.get("enabled"):
                conn.execute(
                    """
                    INSERT INTO trackers (goal_id, metric, target, unit, current)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        goal_id,
                        tracker.get("metric", "Progress").strip() or "Progress",
                        float(tracker.get("target") or 1),
                        tracker.get("unit", "count").strip() or "count",
                        float(tracker.get("current") or 0),
                    ),
                )
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        json_response(self, {"goal": enrich_goal(row, user)})

    def complete_goal(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        goal = get_goal_for_user(int(data["goal_id"]), user["id"])
        if not goal:
            json_response(self, {"error": "Goal not found."}, HTTPStatus.NOT_FOUND)
            return
        if goal["user_id"] != user["id"]:
            json_response(self, {"error": "Only the owner can complete this goal."}, HTTPStatus.FORBIDDEN)
            return
        with db() as conn:
            conn.execute("UPDATE goals SET status = 'complete', completed_at = ? WHERE id = ?", (now_iso(), goal["id"]))
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal["id"],)).fetchone()
        json_response(self, {"goal": enrich_goal(row, user)})

    def update_tracker(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        tracker_id = int(data["tracker_id"])
        with db() as conn:
            tracker = conn.execute(
                """
                SELECT trackers.*, goals.user_id FROM trackers
                JOIN goals ON goals.id = trackers.goal_id
                WHERE trackers.id = ?
                """,
                (tracker_id,),
            ).fetchone()
            if not tracker or tracker["user_id"] != user["id"]:
                json_response(self, {"error": "Tracker not found."}, HTTPStatus.NOT_FOUND)
                return
            conn.execute("UPDATE trackers SET current = ? WHERE id = ?", (float(data["current"]), tracker_id))
        json_response(self, {"ok": True})

    def share_goal(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        goal = get_goal_for_user(int(data["goal_id"]), user["id"])
        email = data.get("email", "").strip().lower()
        if not goal or goal["user_id"] != user["id"]:
            json_response(self, {"error": "Only the owner can share this goal."}, HTTPStatus.FORBIDDEN)
            return
        if not email:
            json_response(self, {"error": "An email is required."}, HTTPStatus.BAD_REQUEST)
            return
        with db() as conn:
            existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            conn.execute(
                """
                INSERT INTO shares (goal_id, owner_id, shared_with_email, accepted_user_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (goal["id"], user["id"], email, existing_user["id"] if existing_user else None, now_iso()),
            )
        json_response(self, {"ok": True, "message": "Goal shared. If they already have an account, it appears for them now."})

    def accept_invite(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        with db() as conn:
            conn.execute(
                """
                UPDATE shares SET accepted_user_id = ?
                WHERE id = ? AND shared_with_email = ?
                """,
                (user["id"], int(data["share_id"]), user["email"]),
            )
        json_response(self, {"ok": True})

    def add_cheer(self, data: Dict[str, Any], user: sqlite3.Row) -> None:
        goal = get_goal_for_user(int(data["goal_id"]), user["id"])
        message = data.get("message", "").strip()
        if not goal:
            json_response(self, {"error": "Goal not found."}, HTTPStatus.NOT_FOUND)
            return
        if not message:
            json_response(self, {"error": "Message is required."}, HTTPStatus.BAD_REQUEST)
            return
        with db() as conn:
            conn.execute(
                "INSERT INTO cheers (goal_id, from_user_id, message, created_at) VALUES (?, ?, ?, ?)",
                (goal["id"], user["id"], message[:240], now_iso()),
            )
        json_response(self, {"ok": True})


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    init_db()
    server = ThreadingHTTPServer((host, port), CountdownerHandler)
    print(f"Countdowner is running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
