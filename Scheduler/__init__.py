import time
from datetime import datetime


def classroom_builder_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.school_selector.selected_value:
        self.schedule_print_box.content = "Please select a school"
        return

    if not self.start_date:
        self.schedule_print_box.content = "Please select a start date"
        return

    # Convert the string date back to a date object for the API call
    start_date = datetime.strptime(self.start_date, "%m-%d-%Y").date()

    # Start the background task
    task_id = anvil.server.call(
        "create_full_classroom_schedule",
        self.school_selector.selected_value,
        start_date,
        None,
        self.COURSE_STRUCTURE,
    )

    # Show initial message
    self.schedule_print_box.content = "The report is being written. Please wait..."

    # Start polling for completion
    self.poll_for_report(task_id)


def poll_for_report(self, task_id):
    """Poll for report completion"""
    # Wait 55 seconds
    time.sleep(55)

    # Check task status
    task = app_tables.background_tasks.get(task_id=task_id)

    if task and task["status"] == "done" and task["output_filename"]:
        # Report is ready
        self.schedule_print_box.content = (
            f"Report completed successfully: {task['output_filename']}"
        )
    elif task and task["status"] == "error":
        # Task failed
        self.schedule_print_box.content = (
            f"Error creating report: {task.get('error', 'Unknown error')}"
        )
    else:
        # Still running, poll again
        self.schedule_print_box.content = "Still generating report... Please wait..."
        anvil.timer.call_after(55, lambda: self.poll_for_report(task_id))


def instructor_scheduler_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.classroom_selector.selected_value:
        self.schedule_print_box.content = "Please select a classroom"
        return

    if (
        not self.instructor1_selector.selected_value
        or not self.instructor2_selector.selected_value
    ):
        self.schedule_print_box.content = "Please select both instructors"
        return

    task_id = anvil.server.call(
        "schedule_instructors_for_classroom",
        self.classroom_selector.selected_value,
        self.instructor1_selector.selected_value,
        self.instructor2_selector.selected_value,
    )

    self.schedule_print_box.content = f"The instructors are being scheduled. Please wait for the process to complete. Do not close this window."
    time.sleep(45)  # Wait for background task to complete

    if task_id:
        instructor_schedule = app_tables.background_tasks.get(task_id=task_id)
        if instructor_schedule and instructor_schedule["status"] == "done":
            formatted_output = (
                f"Instructor Schedule: {instructor_schedule['classroom_name']}\n\n"
            )
            formatted_output += "Instructors have been successfully scheduled."

            self.schedule_print_box.content = f"The instructors have been scheduled successfully:\n\n{formatted_output}\n\nYou can export this file now"
        else:
            self.schedule_print_box.content = "Error scheduling instructors"
    else:
        self.schedule_print_box.content = "Error scheduling instructors"
