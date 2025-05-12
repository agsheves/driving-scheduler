def classroom_builder_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Get the selected school and start date
    school = self.school_selector.selected_value
    start_date = datetime.strptime(self.start_date, "%m-%d-%Y").date()

    # Start the background task
    task_id = anvil.server.call(
        "create_full_classroom_schedule",
        school,
        start_date,
        None,
        self.COURSE_STRUCTURE,
    )

    # Show loading state
    self.schedule_print_box.content = "Building classroom schedule..."

    # Start watching for completion
    self.watch_classroom_task(task_id)


def watch_classroom_task(self, task_id):
    def check_status():
        status = anvil.server.call("check_classroom_task_status", task_id)
        if status == "done":
            self.schedule_print_box.content = "Classroom created successfully!"
            # Refresh the classroom list
            self.refresh_classroom_list()
        elif status == "error":
            self.schedule_print_box.content = "Error creating classroom"
        else:
            # Check again in 2 seconds
            anvil.timer.call_after(2, check_status)

    # Start first check
    check_status()


def instructor_scheduler_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Get the selected classroom and instructors
    classroom = self.classroom_selector.selected_value
    instructor1 = self.instructor1_selector.selected_value
    instructor2 = self.instructor2_selector.selected_value

    # Start the background task
    task_id = anvil.server.call(
        "schedule_instructors_for_classroom",
        classroom,
        instructor1,
        instructor2,
    )

    # Show loading state
    self.schedule_print_box.content = "Scheduling instructors..."

    # Start watching for completion
    self.watch_instructor_task(task_id)


def watch_instructor_task(self, task_id):
    def check_status():
        status = anvil.server.call("check_instructor_task_status", task_id)
        if status == "done":
            self.schedule_print_box.content = "Instructors scheduled successfully!"
            # Refresh the classroom list
            self.refresh_classroom_list()
        elif status == "error":
            self.schedule_print_box.content = "Error scheduling instructors"
        else:
            # Check again in 2 seconds
            anvil.timer.call_after(2, check_status)

    # Start first check
    check_status()
