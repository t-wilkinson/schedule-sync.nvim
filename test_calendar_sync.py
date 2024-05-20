import unittest
from datetime import datetime
from unittest.mock import patch
from calendar_sync import parse_schedule, events_to_text, tasks_to_text, CALENDAR_MAP


class TestScheduleSync(unittest.TestCase):
    def test_parse_schedule_basic(self):
        with open("test-schedule.txt", "w") as file:  # Create a test file
            file.write(
                """
June.
    23.  3  4  5  6  7  8  9
    24. 10 11 12 13 14 15 16
    Mon-17.
        08:00 Breakfast [Personal]
        09:00 Meeting [Work]
        - Grocery shopping
    Tue-18.
        10:30 Dentist appointment [Personal]
        14:00 Work on project [Work]
                """
            )
        events, tasks = parse_schedule("test-schedule.txt")

        # Assert events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0][0]["summary"], "Breakfast")
        self.assertEqual(events[0][1], CALENDAR_MAP["Personal"])
        self.assertEqual(events[1][0]["summary"], "Meeting")
        self.assertEqual(events[1][1], CALENDAR_MAP["Work"])
        self.assertEqual(events[2][0]["summary"], "Dentist appointment")
        self.assertEqual(events[2][1], CALENDAR_MAP["Personal"])

        # Assert tasks
        self.assertEqual(len(tasks), 2)
        self.assertEqual(
            tasks[datetime(year=2024, month=6, day=17)], ["Grocery shopping"]
        )
        self.assertEqual(
            tasks[datetime(year=2024, month=6, day=18)], ["Work on project"]
        )

    def test_events_to_text(self):
        events = [
            (
                {
                    "summary": "Test Event",
                    "start": {"dateTime": "2024-06-17T10:00:00"},
                    "end": {"dateTime": "2024-06-17T11:00:00"},
                },
                "primary",
            ),
        ]
        text = events_to_text(events)
        self.assertEqual(
            text, ["10:00 Test Event [Personal]"]
        )  # Assuming "primary" maps to "Personal"

    def test_tasks_to_text(self):
        tasks = [
            {"summary": "Test Task", "start": {"date": "2024-06-18"}},
        ]
        text = tasks_to_text(tasks)
        self.assertEqual(text, ["- Test Task"])

    # Add more tests for different scenarios, edge cases, and error handling
