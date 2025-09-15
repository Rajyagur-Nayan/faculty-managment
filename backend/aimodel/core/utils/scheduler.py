# core/utils/scheduler.py
from core.models import TimetableSlot, Subject, Room

import datetime
from django.db import transaction

WEEK_DAYS = [1,2,3,4,5,6]  # Mon..Sat
DEFAULT_SLOTS = [
    (datetime.time(9,0), datetime.time(10,0)),
    (datetime.time(10,0), datetime.time(11,0)),
    (datetime.time(11,0), datetime.time(12,0)),
    (datetime.time(13,0), datetime.time(14,0)),
    (datetime.time(14,0), datetime.time(15,0)),
    (datetime.time(15,0), datetime.time(16,0)),
]

@transaction.atomic
def simple_generate_timetable_for_semester(semester):
    """
    Very simple: for each ClassMasterEntry subject, assign slots sequentially to available rooms.
    Overwrites existing TimetableSlot for that semester's subjects.
    """
    # remove existing slots for these subjects
    subs = Subject.objects.filter(semester=semester)
    TimetableSlot.objects.filter(subject__in=subs).delete()

    rooms = list(Room.objects.all()) or []
    room_index = 0

    # subject.weekly_hours: allocate that many slots (assuming 1 hour slots)
    for subject in subs:
        hours = int(round(subject.weekly_hours))
        assigned = 0
        # naive round-robin day and slot
        for day in WEEK_DAYS:
            for start, end in DEFAULT_SLOTS:
                if assigned >= hours:
                    break
                # pick a room
                room = rooms[room_index % len(rooms)] if rooms else None
                room_index += 1
                # faculty from class master
                cm = subject.classmasterentry_set.first()
                faculty = cm.faculty if cm else None
                if not faculty:
                    # skip if no faculty assigned
                    continue
                TimetableSlot.objects.create(
                    day=day, start_time=start, end_time=end,
                    subject=subject, faculty=faculty, room=room,
                    batch=cm.batch if cm else None
                )
                assigned += 1
            if assigned >= hours:
                break
    return True
