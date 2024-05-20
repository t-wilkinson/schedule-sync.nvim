#!/usr/bin/env python3
import re
import os
import datetime
from datetime import timedelta, timezone
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "America/New_York"  # Set your timezone here
CALENDAR_MAP = {
    "Personal": "primary",
    "Work": "primary",
    "Jenn": "2add663ebbe722f0aaca27d7977986fbf98d8a445de8345183119770f0ed9dfc@group.calendar.google.com",
    "tasks": "primary",
}


def fetch_existing_events(service, calendar_id, time_min, time_max):
    """Fetches existing events from the specified calendar within the given time range."""
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def compare_events(new_event, existing_event):
    """Compares two events to determine if they are the same or need modification."""
    if new_event["summary"] != existing_event["summary"]:
        return "modify"  # Different summaries, modify
    if new_event["start"] != existing_event["start"]:
        return "modify"  # Different start times, modify
    if new_event["end"] != existing_event["end"]:
        return "modify"  # Different end times, modify
    return "same"  # Events are the same


def delete_missing_events(service, calendar_id, existing_events, new_events):
    """Deletes events that are in existing_events but not in new_events."""
    for existing_event in existing_events:
        if not any(
            compare_events(new_event[0], existing_event) != "modify"
            for new_event in new_events
        ):
            service.events().delete(
                calendarId=calendar_id, eventId=existing_event["id"]
            ).execute()
            print(f"Event deleted: {existing_event['summary']}")


def events_to_text(events):
    """Converts a list of Google Calendar events into text for the schedule file."""
    lines = []
    for event in events:
        start_time = datetime.datetime.fromisoformat(
            event["start"]["dateTime"]
        ).strftime("%H:%M")
        summary = event["summary"]
        calendar_name = [
            name for name, id in CALENDAR_MAP.items() if id == event["calendarId"]
        ][0]  # Find calendar name
        lines.append(f"{start_time} {summary} [{calendar_name}]")
    return lines


def tasks_to_text(tasks):
    """Converts a list of tasks (represented as all-day events) into text for the schedule file."""
    lines = []
    for task in tasks:
        date = datetime.date.fromisoformat(task["start"]["date"])
        summary = task["summary"]
        lines.append(f"- {summary}")  # Assume tasks are always on the TASK_CALENDAR_ID
    return lines


def get_calendar_service():
    creds = None
    token_file = "token.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES,  # Replace with your credentials file
            )
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


month_pattern = re.compile(r"(\w+)\.")
week_pattern = re.compile(r"^\s*(\d{2})\.")
date_pattern = re.compile(r"^\s*([A-Za-z]{3}-\d{1,2})\.")
time_pattern = re.compile(r"^\s*(\d{2}:\d{2})\s*(.+?)(?:\s*\[(\w+)\])?$")
description_pattern = re.compile(r"^\s{4}(?!-)(.+)")
task_pattern = re.compile(r"^\s*(-)\s*(.+)")
task_pattern = re.compile(
    r"^\s*(-)\s*(.+)", re.MULTILINE
)  # Use MULTILINE to match across lines


def parse_schedule(filename):
    with open(filename, "r") as file:
        content = file.read()

    events = []
    tasks = {}
    current_date = None
    current_year = datetime.date.today().year
    month_name = None
    prev_time_str = None

    for line in content.splitlines():
        month_match = month_pattern.match(line)
        if month_match:
            month_name = month_match.group(1)
            continue
        if not month_name:
            continue

        week_match = week_pattern.match(line)
        date_match = date_pattern.match(line)
        if date_match:
            day_name, day_num_str = date_match.group(1).split("-")
            day_num = int(day_num_str)
            current_date = datetime.datetime.strptime(
                f"{current_year}-{month_name}-{day_num}", "%Y-%B-%d"
            ).date()
            prev_time_str = None

        time_match = time_pattern.match(line)
        task_match = task_pattern.match(line)

        if time_match and current_date:
            event, prev_time_str = parse_time_block(
                line, content, time_match, current_date, prev_time_str
            )
            events.append(event)

        elif task_match and current_date:
            task = task_match.group(2)
            tasks.setdefault(current_date, []).append(task)

    return events, tasks


def parse_time_block(line, content, time_match, current_date, prev_time_str):
    """Parses a time block, including summary, calendar, description, and tasks."""

    time_str, summary, calendar_name = time_match.groups()
    calendar_id = CALENDAR_MAP.get(calendar_name, "primary")
    start_time = datetime.datetime.combine(
        current_date, datetime.datetime.strptime(time_str, "%H:%M").time()
    )

    # Find the next time in the schedule to calculate end_time
    next_time_str = None
    for next_line in content.splitlines()[content.splitlines().index(line) + 1 :]:
        next_time_match = time_pattern.match(next_line)
        if next_time_match:
            next_time_str = next_time_match.group(1)
            break

    if next_time_str:
        end_time = datetime.datetime.combine(
            current_date,
            datetime.datetime.strptime(next_time_str, "%H:%M").time(),
        )
    else:
        end_time = start_time + timedelta(hours=1)

    # Extract description, location, and tasks
    description, location, event_tasks = parse_event_details(content, line)

    # Create event
    event = {
        "summary": summary,
        "description": "\n".join(description),
        "start": {"dateTime": start_time.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_time.isoformat(), "timeZone": TIMEZONE},
    }
    if location:
        event["location"] = location

    return (event, calendar_id), prev_time_str


def parse_event_details(content, current_line):
    """Parses event details (description, location, tasks) from lines following the time block."""

    description = []
    location = None
    tasks = []

    for next_line in content.splitlines()[
        content.splitlines().index(current_line) + 1 :
    ]:
        next_time_match = time_pattern.match(next_line)
        if next_time_match:
            break
        elif next_line.strip().startswith("Location:"):
            location = next_line.strip()[len("Location:") :].strip()
        elif next_line.strip().startswith("Tasks:"):
            continue
        elif next_line.strip().startswith("-"):
            task = next_line.strip()[len("-") :].strip()
            tasks.append(task)
        elif description_match := description_pattern.match(next_line):
            description.append(description_match.group(1))
        elif not next_line.strip():
            continue
        else:
            break

    return description, location, tasks


def sync_from_google(filename):
    service = get_calendar_service()

    # Fetch events from all calendars in the CALENDAR_MAP
    now = datetime.datetime.now(timezone.utc)
    time_min = now - timedelta(days=7)
    time_max = now + timedelta(days=365)

    all_events = []
    for calendar_name, calendar_id in CALENDAR_MAP.items():
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        all_events.extend(events_result.get("items", []))

    # Fetch tasks (all-day events) from the task calendar id
    tasks_result = (
        service.events()
        .list(
            calendarId=CALENDAR_MAP["tasks"],
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    all_tasks = tasks_result.get("items", [])

    # Sort events and tasks by start time/date
    all_events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date")))
    all_tasks.sort(key=lambda t: t["start"]["date"])

    # Generate text for events and tasks
    event_lines = events_to_text(all_events)
    task_lines = tasks_to_text(all_tasks)

    # Update the schedule file
    with open(filename, "w") as file:
        file.write("\n".join(event_lines + task_lines))
        print("Schedule file updated with events and tasks from Google Calendar.")


def sync_to_google(events, tasks):
    service = get_calendar_service()

    # Cache existing events for each calendar
    now = datetime.datetime.now(timezone.utc)
    time_min = now - timedelta(days=7)  # Look back 7 days
    time_max = now + timedelta(days=30)  # Look ahead 1 month

    existing_events_by_calendar = {}
    for event, calendar_id in events:
        if calendar_id not in existing_events_by_calendar:
            existing_events_by_calendar[calendar_id] = fetch_existing_events(
                service, calendar_id, time_min, time_max
            )

    for event, calendar_id in events:
        existing_events = existing_events_by_calendar[calendar_id]
        matching_events = [
            e for e in existing_events if compare_events(event, e) == "same"
        ]
        if matching_events:
            print(f"Event already exists: {event['summary']}")
        else:
            to_modify = [
                e for e in existing_events if compare_events(event, e) == "modify"
            ]
            if to_modify:
                event_to_modify = to_modify[0]
                event_to_modify.update(event)
                service.events().update(
                    calendarId=calendar_id,
                    eventId=event_to_modify["id"],
                    body=event_to_modify,
                ).execute()
                print(f"Event modified: {event['summary']}")
            else:
                service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"Event created: {event['summary']}")

    # Delete missing events
    for calendar_id, existing_events in existing_events_by_calendar.items():
        delete_missing_events(service, calendar_id, existing_events, events)

    for date, task_list in tasks.items():
        for task in task_list:
            # Create an all-day event for each task
            event = {
                "summary": task,
                "start": {"date": date.isoformat()},
                "end": {"date": (date + timedelta(days=1)).isoformat()},
            }
            service.events().insert(
                calendarId=CALENDAR_MAP["tasks"], body=event
            ).execute()
            print(f"Task created: {task} on {date}")


if __name__ == "__main__":
    filename = "test-schedule.txt"
    events, tasks = parse_schedule(filename)
    sync_to_google(events, tasks)
    sync_from_google(filename)
