---
name: Things 3 Integration
description: Read and manage tasks in Things 3 task manager. Use when user wants to view, create, update, or complete todos and projects in Things 3. macOS only.
version: 1.0.0
---

# Things 3 Task Manager Integration

## Overview

This skill provides full read/write access to Things 3 task manager on macOS. Read operations query the SQLite database directly (fast, no app needed). Write operations use the Things URL Scheme (requires Things 3 running).

For advanced usage and API details, see REFERENCE.md.

## Quick Start

```bash
# Get today's tasks
python ~/.claude/skills/things3/scripts/things3.py today

# Search for tasks
python ~/.claude/skills/things3/scripts/things3.py search "meeting"

# Get all projects
python ~/.claude/skills/things3/scripts/things3.py projects
```

Output is JSON. No external dependencies required.

## Read Commands

| Command | Description |
|---------|-------------|
| `today` | Today's tasks (scheduled + overdue) |
| `inbox` | Inbox tasks |
| `upcoming` | Future scheduled tasks |
| `anytime` | Anytime tasks (no specific date) |
| `someday` | Someday tasks (deferred) |
| `projects` | All active projects |
| `areas` | All areas |
| `tags` | All tags |
| `deadlines` | Tasks with deadlines |
| `logbook` | Completed/canceled tasks |
| `completed N` | Completed in last N days |
| `search "query"` | Search by title/notes |
| `get UUID` | Get specific task by UUID |

### Examples

```bash
# View today's tasks
python ~/.claude/skills/things3/scripts/things3.py today

# Search for tasks containing "report"
python ~/.claude/skills/things3/scripts/things3.py search "report"

# Get tasks completed in last 7 days
python ~/.claude/skills/things3/scripts/things3.py completed 7

# Get specific task details
python ~/.claude/skills/things3/scripts/things3.py get "ABC123-UUID"
```

## Write Operations

Write operations require importing the module:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/things3/scripts"))
from things3 import create_todo, create_project, update_todo, complete_todo, show
```

### Create Todo
```python
create_todo(
    title="Buy groceries",           # Required
    notes="Milk, eggs, bread",       # Optional
    when="tomorrow",                 # today, tomorrow, evening, anytime, someday, YYYY-MM-DD
    deadline="2025-01-20",           # Optional, YYYY-MM-DD
    tags="shopping,errands",         # Optional, comma-separated
    list_title="Personal",           # Optional, project or area name
    reveal=True                      # Show in Things after creation
)
```

### Create Project
```python
create_project(
    title="Q1 Planning",
    notes="Quarterly planning tasks",
    area_title="Work",               # Optional, area name
    when="2025-01-15",
    deadline="2025-03-31"
)
```

### Update/Complete Todo
```python
# Update task
update_todo(
    uuid="task-uuid",                # Required, from read operations
    title="New title",               # Optional
    when="next monday",              # Optional
    completed=True                   # Optional, mark done
)

# Quick complete
complete_todo("task-uuid")
```

### Show in Things App
```python
show(uuid="task-uuid")              # Show specific task
show(list_name="today")             # Show list: inbox, today, upcoming, anytime, someday, logbook
```

## Task JSON Structure

```json
{
  "uuid": "ABC123",
  "title": "Task title",
  "notes": "Description",
  "type": "to-do",           // "to-do", "project", "heading"
  "status": "incomplete",    // "incomplete", "completed", "canceled"
  "start": "Anytime",        // "Inbox", "Anytime", "Someday"
  "start_date": "2025-01-15",
  "deadline": "2025-01-20",
  "project": "project-uuid",
  "area": "area-uuid",
  "created": "2025-01-10 09:00:00",
  "modified": "2025-01-10 10:30:00"
}
```

## When Values

| Value | Effect |
|-------|--------|
| `today` | Schedule for today |
| `tomorrow` | Schedule for tomorrow |
| `evening` | Schedule for this evening |
| `anytime` | No date, shows in Anytime |
| `someday` | Deferred, shows in Someday |
| `YYYY-MM-DD` | Specific date |
| `next monday` | Natural language (URL Scheme) |
| `in 3 days` | Relative date (URL Scheme) |

## Requirements

- macOS with Things 3 installed
- Python 3 (standard library only)
- Things 3 must be running for write operations
