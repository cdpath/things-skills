#!/usr/bin/env python3
"""
Things 3 Python interface - No external dependencies required.
Reads from Things 3 SQLite database and writes via URL Scheme.
"""

import sqlite3
import subprocess
import json
import glob
import os
from datetime import datetime, date
from urllib.parse import urlencode, quote
from typing import Optional, List, Dict, Any


# Database path pattern
DB_PATH_PATTERN = os.path.expanduser(
    "~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things Database.thingsdatabase/main.sqlite"
)

# Task types
TYPE_TODO = 0
TYPE_PROJECT = 1
TYPE_HEADING = 2

# Task status
STATUS_INCOMPLETE = 0
STATUS_CANCELED = 2
STATUS_COMPLETED = 3

# Start values
START_INBOX = 0
START_ANYTIME = 1
START_SOMEDAY = 2


def _get_db_path() -> str:
    """Find the Things 3 database path."""
    paths = glob.glob(DB_PATH_PATTERN)
    if not paths:
        raise FileNotFoundError("Things 3 database not found. Is Things 3 installed?")
    return paths[0]


def _connect() -> sqlite3.Connection:
    """Connect to the Things 3 database."""
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _things_date_to_str(things_date: Optional[int]) -> Optional[str]:
    """Convert Things date integer to ISO date string.
    
    Things stores dates as: YYYYYYYYYYYMMMMDDDDD0000000 in binary.
    - 11 bits for year
    - 4 bits for month
    - 5 bits for day
    - 7 bits unused (zeros)
    """
    if things_date is None or things_date == 0:
        return None
    
    y_mask = 0b111111111110000000000000000  # 134152192
    m_mask = 0b000000000001111000000000000  # 61440
    d_mask = 0b000000000000000111110000000  # 3968
    
    year = (things_date & y_mask) >> 16
    month = (things_date & m_mask) >> 12
    day = (things_date & d_mask) >> 7
    
    if year == 0 or month == 0 or day == 0:
        return None
    
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _unix_to_str(timestamp: Optional[float]) -> Optional[str]:
    """Convert Unix timestamp to ISO datetime string."""
    if timestamp is None:
        return None
    # creationDate/userModificationDate/stopDate use standard Unix epoch (1970)
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.isoformat(sep=" ", timespec="seconds")
    except (OSError, ValueError):
        return None


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a database row to a dictionary with human-readable values."""
    d = dict(row)
    
    # Convert type
    type_map = {TYPE_TODO: "to-do", TYPE_PROJECT: "project", TYPE_HEADING: "heading"}
    d["type"] = type_map.get(d.get("type"), d.get("type"))
    
    # Convert status
    status_map = {STATUS_INCOMPLETE: "incomplete", STATUS_CANCELED: "canceled", STATUS_COMPLETED: "completed"}
    d["status"] = status_map.get(d.get("status"), d.get("status"))
    
    # Convert start
    start_map = {START_INBOX: "Inbox", START_ANYTIME: "Anytime", START_SOMEDAY: "Someday"}
    d["start"] = start_map.get(d.get("start"), d.get("start"))
    
    # Convert dates
    if "startDate" in d:
        d["start_date"] = _things_date_to_str(d.pop("startDate"))
    if "deadline" in d:
        d["deadline"] = _things_date_to_str(d.get("deadline"))
    if "creationDate" in d:
        d["created"] = _unix_to_str(d.pop("creationDate"))
    if "userModificationDate" in d:
        d["modified"] = _unix_to_str(d.pop("userModificationDate"))
    if "stopDate" in d:
        d["stop_date"] = _unix_to_str(d.pop("stopDate"))
    
    return d


# ============== READ OPERATIONS ==============

def _today_thingsdate() -> int:
    """Get today's date as Things date format."""
    d = date.today()
    return (d.year << 16) | (d.month << 12) | (d.day << 7)


def today() -> List[Dict[str, Any]]:
    """Get today's tasks.
    
    Includes:
    - Regular today tasks (scheduled for today or earlier, start=Anytime)
    - Unconfirmed scheduled tasks (past start_date, start=Someday) - yellow dot
    - Unconfirmed overdue tasks (no start_date, overdue deadline)
    """
    conn = _connect()
    today_int = _today_thingsdate()
    
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               todayIndex, project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND rt1_recurrenceRule IS NULL
          AND (
              -- Regular today tasks
              (start = 1 AND startDate IS NOT NULL AND startDate <= ?)
              -- Unconfirmed scheduled tasks (yellow dot)
              OR (start = 2 AND startDate IS NOT NULL AND startDate <= ?)
              -- Unconfirmed overdue tasks
              OR (startDate IS NULL AND deadline IS NOT NULL AND deadline < ? AND deadlineSuppressionDate IS NULL)
          )
        ORDER BY todayIndex, startDate
    """
    cursor = conn.execute(query, (today_int, today_int, today_int))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def inbox() -> List[Dict[str, Any]]:
    """Get inbox tasks."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND rt1_recurrenceRule IS NULL
          AND start = 0
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def upcoming() -> List[Dict[str, Any]]:
    """Get upcoming tasks (scheduled for future, start=Someday)."""
    conn = _connect()
    today_int = _today_thingsdate()
    
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND rt1_recurrenceRule IS NULL
          AND start = 2
          AND startDate IS NOT NULL
          AND startDate > ?
        ORDER BY startDate, "index"
    """
    cursor = conn.execute(query, (today_int,))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def anytime() -> List[Dict[str, Any]]:
    """Get anytime tasks (start=Anytime, no scheduled date)."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND rt1_recurrenceRule IS NULL
          AND start = 1
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def someday() -> List[Dict[str, Any]]:
    """Get someday tasks (no start_date, start=Someday)."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND rt1_recurrenceRule IS NULL
          AND start = 2
          AND startDate IS NULL
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def projects() -> List[Dict[str, Any]]:
    """Get all projects."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND type = 1
          AND status = 0
          AND rt1_recurrenceRule IS NULL
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def areas() -> List[Dict[str, Any]]:
    """Get all areas."""
    conn = _connect()
    query = """
        SELECT uuid, title
        FROM TMArea 
        WHERE visible = 1
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def tags() -> List[Dict[str, Any]]:
    """Get all tags."""
    conn = _connect()
    query = """
        SELECT uuid, title, shortcut, parent
        FROM TMTag 
        ORDER BY "index"
    """
    cursor = conn.execute(query)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def completed(last_days: int = 7) -> List[Dict[str, Any]]:
    """Get completed tasks from last N days."""
    conn = _connect()
    # Mac epoch timestamp for N days ago
    mac_epoch = datetime(2001, 1, 1)
    cutoff = (datetime.now() - mac_epoch).total_seconds() - (last_days * 86400)
    
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate, stopDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 3
          AND type = 0
          AND stopDate > ?
        ORDER BY stopDate DESC
    """
    cursor = conn.execute(query, (cutoff,))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def logbook() -> List[Dict[str, Any]]:
    """Get logbook (completed and canceled tasks)."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate, stopDate
        FROM TMTask 
        WHERE trashed = 0 
          AND (status = 3 OR status = 2)
          AND type = 0
        ORDER BY stopDate DESC
        LIMIT 100
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def search(query_str: str) -> List[Dict[str, Any]]:
    """Search tasks by title or notes."""
    conn = _connect()
    pattern = f"%{query_str}%"
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND (title LIKE ? OR notes LIKE ?)
        ORDER BY userModificationDate DESC
        LIMIT 50
    """
    cursor = conn.execute(query, (pattern, pattern))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def get(uuid: str) -> Optional[Dict[str, Any]]:
    """Get a specific task by UUID."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, heading, creationDate, userModificationDate, stopDate
        FROM TMTask 
        WHERE uuid = ?
    """
    cursor = conn.execute(query, (uuid,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def deadlines() -> List[Dict[str, Any]]:
    """Get tasks with deadlines."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, area, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND status = 0
          AND type = 0
          AND deadline IS NOT NULL
        ORDER BY deadline
    """
    cursor = conn.execute(query)
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def project_todos(project_uuid: str) -> List[Dict[str, Any]]:
    """Get todos for a specific project."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               heading, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND type = 0
          AND project = ?
        ORDER BY "index"
    """
    cursor = conn.execute(query, (project_uuid,))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def area_items(area_uuid: str) -> List[Dict[str, Any]]:
    """Get todos and projects for a specific area."""
    conn = _connect()
    query = """
        SELECT uuid, title, notes, type, status, start, startDate, deadline,
               project, creationDate, userModificationDate
        FROM TMTask 
        WHERE trashed = 0 
          AND area = ?
          AND status = 0
        ORDER BY type, "index"
    """
    cursor = conn.execute(query, (area_uuid,))
    result = [_row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


# ============== WRITE OPERATIONS (via URL Scheme) ==============

def get_auth_token() -> Optional[str]:
    """Get the Things URL scheme authentication token from database.
    
    TMSettings table has only one row containing the auth token.
    """
    try:
        conn = _connect()
        query = "SELECT uriSchemeAuthenticationToken FROM TMSettings LIMIT 1"
        cursor = conn.execute(query)
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _build_url(command: str, **params) -> str:
    """Build a Things URL scheme."""
    filtered = {k: v for k, v in params.items() if v is not None}
    for k, v in filtered.items():
        if isinstance(v, bool):
            filtered[k] = "true" if v else "false"
    
    query = urlencode(filtered, quote_via=quote) if filtered else ""
    return f"things:///{command}?{query}" if query else f"things:///{command}"


def _run_url(url: str) -> bool:
    """Open a Things URL (executes the command)."""
    try:
        subprocess.run(["open", "-g", url], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def create_todo(
    title: str,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    list_title: str = None,
    heading: str = None,
    completed: bool = None,
    reveal: bool = False
) -> bool:
    """
    Create a new todo.
    
    Args:
        title: Todo title
        notes: Notes/description
        when: When to schedule (today, tomorrow, evening, anytime, someday, YYYY-MM-DD)
        deadline: Deadline date (YYYY-MM-DD)
        tags: Comma-separated tag names
        list_title: Project or area title to add to
        heading: Heading within the project
        completed: Mark as completed
        reveal: Show in Things after creation
    """
    url = _build_url(
        "add",
        title=title,
        notes=notes,
        when=when,
        deadline=deadline,
        tags=tags,
        list=list_title,
        heading=heading,
        completed=completed,
        reveal="true" if reveal else "false"
    )
    return _run_url(url)


def create_project(
    title: str,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    area_title: str = None,
    reveal: bool = False
) -> bool:
    """
    Create a new project.
    
    Args:
        title: Project title
        notes: Notes/description
        when: When to schedule
        deadline: Deadline date
        tags: Comma-separated tag names
        area_title: Area to add project to
        reveal: Show in Things after creation
    """
    url = _build_url(
        "add-project",
        title=title,
        notes=notes,
        when=when,
        deadline=deadline,
        tags=tags,
        area=area_title,
        reveal="true" if reveal else "false"
    )
    return _run_url(url)


def update_todo(
    uuid: str,
    title: str = None,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    completed: bool = None
) -> bool:
    """
    Update an existing todo.
    
    Args:
        uuid: Todo UUID (required)
        title: New title
        notes: New notes (prepend/append with special syntax)
        when: New schedule
        deadline: New deadline
        tags: New tags
        completed: Mark as completed/incomplete
    """
    # Update requires auth-token
    auth_token = get_auth_token()
    if not auth_token:
        print("Warning: Could not get auth-token, update may fail")
    
    url = _build_url(
        "update",
        id=uuid,
        title=title,
        notes=notes,
        when=when,
        deadline=deadline,
        tags=tags,
        completed=completed,
        **({"auth-token": auth_token} if auth_token else {})
    )
    return _run_url(url)


def complete_todo(uuid: str) -> bool:
    """Mark a todo as completed."""
    return update_todo(uuid, completed=True)


def show(uuid: str = None, list_name: str = None) -> bool:
    """
    Show a specific item or list in Things.
    
    Args:
        uuid: Item UUID to show
        list_name: Built-in list (inbox, today, upcoming, anytime, someday, logbook, trash)
    """
    if uuid:
        url = _build_url("show", id=uuid)
    elif list_name:
        url = _build_url("show", id=list_name)
    else:
        url = "things:///show"
    return _run_url(url)


# ============== CLI ==============

if __name__ == "__main__":
    import sys
    
    commands = {
        "today": today,
        "inbox": inbox,
        "upcoming": upcoming,
        "anytime": anytime,
        "someday": someday,
        "projects": projects,
        "areas": areas,
        "tags": tags,
        "deadlines": deadlines,
        "logbook": logbook,
    }
    
    if len(sys.argv) < 2:
        print("Usage: things3.py <command> [args]")
        print(f"Commands: {', '.join(commands.keys())}, search <query>, get <uuid>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd in commands:
        result = commands[cmd]()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "search" and len(sys.argv) > 2:
        result = search(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "get" and len(sys.argv) > 2:
        result = get(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "completed":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        result = completed(days)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
