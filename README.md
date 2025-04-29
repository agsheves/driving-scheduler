# Driving Schedule App

# Framework
Built in an [anvil.works](anvil.works) framework running python in the background 🐍

# Set up

## Availability

All scheduling -- availability, 'ghost lessons', and booked lessons -- is based on fixed 'time_slots'. These are top-level fixed two-hour blocks of time as below (current as of April 29, 2025). Breaks are also defined for clarity.

```
availability_time_slots = {
    "time_slot_1": {
        "start_time": "08:00",
        "end_time": "10:00",
        "seasonal": "no",
        "term_days": ["Saturday", "Sunday"],
        "vacation": "all",
        "is_break": False
    },
    "time_slot_2": {
        "start_time": "10:15",
        "end_time": "12:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_3": {
        "start_time": "13:15",
        "end_time": "15:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_4": {
        "start_time": "15:45",
        "end_time": "17:45",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_5": {
        "start_time": "18:00",
        "end_time": "20:00",
        "seasonal": ["spring", "summer"],
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_6": {
        "start_time": "18:30",
        "end_time": "20:30",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_break_am": {
        "start_time": "10:00",
        "end_time": "10:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
    },
    "time_slot_break_lunch": {
        "start_time": "12:15",
        "end_time": "13:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
    },
    "time_slot_break_pm": {
        "start_time": "15:15",
        "end_time": "15:45",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
    }
}
```

## Time Slot References

Time slots have a day reference as above and are then referenced by year-week_number-time slot. That means that each ```time_slot``` has a unique, non repeatable ```time_slot_id```
