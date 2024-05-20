import unittest
from unittest.mock import patch
import datetime
from schedule_sync import CALENDAR_MAP, parse_schedule, events_to_text, tasks_to_text


class TestScheduleSync(unittest.TestCase):
    def setUp(self):
        with open("test_schedule.txt", "w") as file:
            file.write(
                """
June.
    23.  3  4  5  6  7  8  9
    24. 10 11 12 13 14 15 16
    Mon-17.
        08:00 Breakfast [Personal]
            Location: Kitchen
            Eat some eggs
        09:00 Meeting [Work]
            Important meeting with clients.
            Tasks:
            - Discuss project timeline
            - Finalize budget
    Tue-18.
        10:30 Dentist appointment [Personal]
                """
            )

    def test_parse_schedule_with_description_and_tasks(self):
        events, tasks = parse_schedule("test_schedule.txt")

        # Assert events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0][0]["summary"], "Breakfast")
        self.assertEqual(
            events[0][1], CALENDAR_MAP["Personal"]
        )  # Replace with the actual ID
        self.assertEqual(events[0][0]["description"], "Eat some eggs")
        self.assertEqual(events[0][0]["location"], "Kitchen")
        self.assertEqual(events[1][0]["summary"], "Meeting")
        self.assertEqual(
            events[1][1], CALENDAR_MAP["Work"]
        )  # Replace with the actual ID
        self.assertEqual(
            events[1][0]["description"],
            "Important meeting with clients.\n- Discuss project timeline\n- Finalize budget",
        )
        self.assertEqual(events[2][0]["summary"], "Dentist appointment")
        self.assertEqual(
            events[2][1], CALENDAR_MAP["Personal"]
        )  # Replace with the actual ID

        # Assert tasks
        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            tasks[datetime.date(2024, 6, 17)],
            ["Discuss project timeline", "Finalize budget"],
        )

    def test_parse_schedule_time_calculation(self):
        events, _ = parse_schedule("test_schedule.txt")

        # Assert correct time calculation for the first event
        self.assertEqual(events[0][0]["start"]["dateTime"], "2024-06-17T08:00:00-04:00")
        self.assertEqual(events[0][0]["end"]["dateTime"], "2024-06-17T09:00:00-04:00")

        # Assert correct time calculation for the second event (should end at 10:30 due to the next event)
        self.assertEqual(events[1][0]["start"]["dateTime"], "2024-06-17T09:00:00-04:00")
        self.assertEqual(events[1][0]["end"]["dateTime"], "2024-06-17T10:30:00-04:00")

    # Add more tests for events_to_text and tasks_to_text

    # (You might also want to add tests for sync_to_google and sync_from_google,
    # but these will require mocking the Google Calendar API interactions)


if __name__ == "__main__":
    unittest.main()
