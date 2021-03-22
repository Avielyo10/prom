"""
Validators
"""
import datetime


def validate_time(time=None):
    if isinstance(time, datetime.datetime):
        return time
    if time is None:
        return datetime.datetime.utcnow()  # <-- get time in UTC
    return datetime.datetime.fromisoformat(time)
