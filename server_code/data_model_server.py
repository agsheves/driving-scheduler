import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta


@anvil.server.callable
def create_class_session(class_number, start_time, instructor):
    """
    Create a new class session
    Args:
        class_number (int): 1-15 for regular classes, 0 for orientation
        start_time (datetime): When the class starts
        instructor: User object of the instructor
    """
    duration = 1  # hours
    if class_number == 0:  # orientation
        duration = 1
    elif 1 <= class_number <= 15:
        duration = 1
    else:
        raise ValueError("Invalid class number")

    end_time = start_time + timedelta(hours=duration)

    return app_tables.class_sessions.add_row(
        class_number=class_number,
        start_time=start_time,
        end_time=end_time,
        instructor=instructor,
        max_capacity=30,
        current_enrollment=0,
        status="scheduled",
    )


@anvil.server.callable
def enroll_student_in_class(student, class_session):
    """
    Enroll a student in a class session
    Args:
        student: User object of the student
        class_session: Class session object
    """
    # Check if class is full
    if class_session["current_enrollment"] >= class_session["max_capacity"]:
        raise ValueError("Class is full")

    # Check if student is already enrolled
    existing_enrollment = app_tables.class_enrollments.get(
        student=student, class_session=class_session
    )
    if existing_enrollment:
        raise ValueError("Student is already enrolled in this class")

    # Create enrollment
    return app_tables.class_enrollments.add_row(
        student=student,
        class_session=class_session,
        status="enrolled",
        enrollment_date=datetime.now(),
    )


@anvil.server.callable
def get_student_class_schedule(student, start_date=None, end_date=None):
    """
    Get a student's class schedule within a date range
    """
    if start_date is None:
        start_date = datetime.now().date()
    if end_date is None:
        end_date = start_date + timedelta(days=30)

    enrollments = app_tables.class_enrollments.search(
        student=student,
        class_session=q.and_(
            q.fetch_only("start_time") >= start_date,
            q.fetch_only("start_time") <= end_date,
        ),
    )

    return [
        {
            "class_number": e["class_session"]["class_number"],
            "start_time": e["class_session"]["start_time"],
            "end_time": e["class_session"]["end_time"],
            "instructor": e["class_session"]["instructor"]["firstName"],
            "status": e["status"],
        }
        for e in enrollments
    ]


@anvil.server.callable
def get_available_class_sessions(class_number, start_date=None, end_date=None):
    """
    Get available class sessions for a specific class number
    """
    if start_date is None:
        start_date = datetime.now().date()
    if end_date is None:
        end_date = start_date + timedelta(days=30)

    sessions = app_tables.class_sessions.search(
        class_number=class_number,
        start_time=q.and_(
            q.fetch_only("start_time") >= start_date,
            q.fetch_only("start_time") <= end_date,
        ),
        status="scheduled",
    )

    return [
        {
            "id": s.get_id(),
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "instructor": s["instructor"]["firstName"],
            "current_enrollment": s["current_enrollment"],
            "max_capacity": s["max_capacity"],
        }
        for s in sessions
        if s["current_enrollment"] < s["max_capacity"]
    ]
