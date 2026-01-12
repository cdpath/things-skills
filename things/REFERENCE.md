# Things 3 Advanced Reference

This document contains advanced API details, internal implementation notes, and troubleshooting information.

## Database Details

### Location
Things 3 stores data in a SQLite database at:
```
~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things Database.thingsdatabase/main.sqlite
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `TMTask` | All tasks (todos, projects, headings) |
| `TMArea` | Areas |
| `TMTag` | Tags |
| `TMTaskTag` | Task-tag relationships |
| `TMChecklistItem` | Checklist items within todos |

### Task Types (TMTask.type)

| Value | Type |
|-------|------|
| 0 | To-do |
| 1 | Project |
| 2 | Heading |

### Task Status (TMTask.status)

| Value | Status |
|-------|--------|
| 0 | Incomplete |
| 2 | Canceled |
| 3 | Completed |

### Start Values (TMTask.start)

| Value | List |
|-------|------|
| 0 | Inbox |
| 1 | Anytime |
| 2 | Someday |

## Date Formats

### Things Date (startDate, deadline)
Stored as INTEGER with binary format: `YYYYYYYYYYYMMMMDDDDD0000000`
- 11 bits: Year
- 4 bits: Month
- 5 bits: Day
- 7 bits: Unused (zeros)

```python
# Encode
def encode_thingsdate(year, month, day):
    return (year << 16) | (month << 12) | (day << 7)

# Decode
def decode_thingsdate(thingsdate):
    y_mask = 0b111111111110000000000000000
    m_mask = 0b000000000001111000000000000
    d_mask = 0b000000000000000111110000000
    year = (thingsdate & y_mask) >> 16
    month = (thingsdate & m_mask) >> 12
    day = (thingsdate & d_mask) >> 7
    return year, month, day
```

### Unix Timestamps (creationDate, userModificationDate, stopDate)
Standard Unix epoch (seconds since 1970-01-01 00:00:00 UTC).

## URL Scheme Reference

### Base URL
```
things:///<command>?<parameters>
```

### Commands

| Command | Purpose |
|---------|---------|
| `add` | Create new todo |
| `add-project` | Create new project |
| `update` | Update existing todo |
| `update-project` | Update existing project |
| `show` | Show item or list in app |

### Add Todo Parameters

| Parameter | Description |
|-----------|-------------|
| `title` | Todo title (required) |
| `notes` | Notes/description |
| `when` | Schedule: today, tomorrow, evening, anytime, someday, YYYY-MM-DD, natural language |
| `deadline` | Deadline date |
| `tags` | Comma-separated tag names |
| `list` | Project or area title to add to |
| `list-id` | Project or area UUID |
| `heading` | Heading title within project |
| `completed` | true/false |
| `reveal` | true/false - show in app |
| `auth-token` | Required for update operations |

### Update Parameters

| Parameter | Description |
|-----------|-------------|
| `id` | Task UUID (required) |
| `auth-token` | Auth token from TMSettings |
| `title` | New title |
| `notes` | New notes (use `prepend-notes` or `append-notes` for partial updates) |
| `when` | New schedule |
| `deadline` | New deadline |
| `tags` | Replace tags |
| `add-tags` | Add tags |
| `completed` | true/false |
| `canceled` | true/false |

## Python API Details

### Read Functions

```python
# All functions return List[Dict] or Dict

today() -> List[Dict]
# Returns tasks that appear in Today view:
# - Scheduled for today or earlier (start=Anytime)
# - Unconfirmed scheduled tasks (start=Someday, past start_date) - yellow dot
# - Overdue tasks (past deadline, not suppressed)

inbox() -> List[Dict]
# Tasks in Inbox (start=0)

upcoming() -> List[Dict]
# Future scheduled tasks (start=Someday, future start_date)

anytime() -> List[Dict]
# Anytime tasks (start=Anytime, no start_date)

someday() -> List[Dict]
# Someday tasks (start=Someday, no start_date)

projects() -> List[Dict]
# Active projects (type=1, status=0)

areas() -> List[Dict]
# Visible areas

tags() -> List[Dict]
# All tags

deadlines() -> List[Dict]
# Tasks with deadlines, sorted by deadline

logbook() -> List[Dict]
# Completed and canceled tasks, sorted by stop_date

completed(last_days: int = 7) -> List[Dict]
# Completed tasks within last N days

search(query: str) -> List[Dict]
# Search by title or notes (LIKE %query%)

get(uuid: str) -> Optional[Dict]
# Get specific task by UUID

project_todos(project_uuid: str) -> List[Dict]
# Get todos for a specific project

area_items(area_uuid: str) -> List[Dict]
# Get todos and projects for a specific area
```

### Write Functions

```python
create_todo(
    title: str,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    list_title: str = None,
    heading: str = None,
    completed: bool = None,
    reveal: bool = False
) -> bool

create_project(
    title: str,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    area_title: str = None,
    reveal: bool = False
) -> bool

update_todo(
    uuid: str,
    title: str = None,
    notes: str = None,
    when: str = None,
    deadline: str = None,
    tags: str = None,
    completed: bool = None
) -> bool

complete_todo(uuid: str) -> bool

show(uuid: str = None, list_name: str = None) -> bool
```

## Troubleshooting

### Database Not Found
```
FileNotFoundError: Things 3 database not found
```
- Ensure Things 3 is installed
- Check if the app has been opened at least once

### Write Operations Not Working
- Ensure Things 3 app is running
- Check if the task UUID is correct
- Some operations require the auth token (handled automatically for `update`)

### Date Parsing Errors
- Things dates use a special binary format, not Unix timestamps
- Use the decode functions provided above

### Repeating Tasks
Repeating task templates are filtered out (rt1_recurrenceRule IS NULL). Only actual task instances are returned.

## License

This skill uses the Things 3 database format and URL Scheme as documented by Cultured Code. Things 3 is a product of Cultured Code.
