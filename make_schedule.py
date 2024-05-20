#!/usr/bin/env python3
# Generate a yearly schedule for my note system
import calendar
from datetime import datetime
import argparse
import errno


def print_time_block(block_name, start_hour, end_hour):
    print(f"            {block_name}.")
    for hour in range(start_hour, end_hour):
        print(f"                {hour:02}:00")


def print_daily_schedule(year, month, day):
    date = datetime(year, month, day)
    print(f"        {calendar.day_abbr[date.weekday()]}-{day}.")
    print_time_block("Morning", 6, 12)
    print_time_block("Midday", 12, 17)
    print_time_block("Evening", 17, 24)


def print_monthly_calendar(year, month):
    cal = calendar.Calendar()
    month_name = calendar.month_name[month]
    print(f"{month_name}.")
    print("       Mo Tu We Th Fr Sa Su")

    for week in cal.monthdayscalendar(year, month):
        # Get the week number for the first day of the week
        week_num = datetime(year, month, week[0] or 1).isocalendar()[1]
        week_str = " ".join(f"{day:2}" if day != 0 else "  " for day in week)
        print(f"   {week_num:2}. {week_str}")

        for day in week:
            if day != 0:
                print_daily_schedule(year, month, day)


def generate_calendar(year, month=None):
    if month:
        print_monthly_calendar(year, month)
    else:
        for month in range(1, 13):
            print_monthly_calendar(year, month)


def main():
    parser = argparse.ArgumentParser(description="Generate a calendar.")
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        default=datetime.now().year,
        help="Year to generate the calendar for, defaults to current year.",
    )
    parser.add_argument(
        "-m",
        "--month",
        type=int,
        choices=range(1, 13),
        help="Month to generate the calendar for, if not specified, the whole year is generated.",
    )
    args = parser.parse_args()

    if args.month and args.year:
        generate_calendar(args.year, args.month)
    elif args.month:
        generate_calendar(datetime.now().year, args.month)
    else:
        generate_calendar(args.year)


if __name__ == "__main__":
    try:
        main()
    except IOError as e:
        if e.errno == errno.EPIPE:
            pass
