def test_schedule_builder_button_click(self, **event_args):
    result = anvil.server.call("test_program_schedule")
    if result["success"]:
        formatted_schedule = result["formatted_output"]
        self.schedule_print_box.content = formatted_schedule
    else:
        self.schedule_print_box.content = "Error"
