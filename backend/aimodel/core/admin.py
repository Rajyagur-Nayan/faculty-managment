from django.contrib import admin
from django.contrib import admin
from .models import (
    User,
     Holiday,
     AttendanceRecord
)
from .models import Event
from django.contrib import admin
from django.utils.html import format_html
from .models import Student, Subject, AttendanceRecord,Teacher,Quiz,StudentProfile
from django.contrib.auth import get_user_model
from .models import Timetable
import json


# -----------------------------
# 1️⃣ Custom User Admin
# -----------------------------
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('role','is_staff','is_superuser','groups','user_permissions')}),
        ('Important dates', {'fields': ('last_login','date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

# -----------------------------
# Quiz admin
# -----------------------------
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("topic", "question", "answer", "created_at","semester")
    search_fields = ("topic", "question", "answer")
    list_filter = ("topic", "created_at")
    ordering = ("-created_at",)


# --------------
# teacher admin
# --------------
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("id", "name",)
    search_fields = ("name",)



# -----------------------------
# 🔟 Holiday Admin
# -----------------------------
@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('date', 'name','description')
    search_fields = ('name',)
    list_filter = ('date',)

# --------
#  event 
# --------
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'event_datetime', 'description')  # columns shown in list view
    list_filter = ('event_datetime',)  # add a filter sidebar by date
    search_fields = ('title', 'description')  # add a search box
    ordering = ('event_datetime',)  # default ordering by datetime

# ------------------
#  attendance table 
#  ------------------

User = get_user_model()


# ----------
# student
# -----------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """
    Admin for Student model.

    - Shows key fields in list view.
    - Allows searching by student_id, name, and enrollment (if you store enrollment separately).
    - Filters by semester and division.
    - student_id is assumed to be the primary key (e.g., enrollment number).
    """
    list_display = ("student_id", "name", "semester", "division", "gender", "created_at_display")
    list_display_links = ("student_id", "name")
    search_fields = ("student_id", "name")
    list_filter = ("semester", "division")
    ordering = ("semester", "division", "student_id")
    readonly_fields = ("created_at_display",)

    def created_at_display(self, obj):
        # If you have a timestamp field like created_at on Student, show it; otherwise hide gracefully.
        return getattr(obj, "created_at", "")
    created_at_display.short_description = "Created At"


class AttendanceRecordInline(admin.TabularInline):
    """
    Inline admin so that attendance records for a student show up on the Student admin page.
    Use a small number of fields so the inline is readable.
    """
    model = AttendanceRecord
    extra = 0  # don't show empty extra rows by default
    fields = ("subject", "date", "status")
    readonly_fields = ()
    show_change_link = True
    # If attendance table is large, consider using raw_id_fields or disable inline for performance.


# ------------
# subject
# ------------

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """
    Admin for AttendanceRecord model.

    - Useful list display & filters to quickly find records by date, subject, student, or status.
    - raw_id_fields for student/subject for better performance with many rows.
    - Adds an admin action to toggle status (Present <-> Absent) for selected records.
    """
    list_display = ("student_link", "subject", "date", "status", "teacher_for_subject")
    list_filter = ("subject", "date", "status", "subject__semester")
    search_fields = ("student__student_id", "student__name", "subject__name")
    ordering = ("-date", "subject", "student__student_id")
    raw_id_fields = ("student", "subject")
    date_hierarchy = "date"  # quick navigation by date

    actions = ["mark_present", "mark_absent", "toggle_status"]

    def student_link(self, obj):
        # Show student id and name compactly
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.student.student_id,
            obj.student.name
        )
    student_link.short_description = "Student"

    def teacher_for_subject(self, obj):
        # Show teacher's name (Teacher model only has 'name')
        if obj.subject and obj.subject.teacher:
            return obj.subject.teacher.name
        return "-"
    teacher_for_subject.short_description = "Teacher"

    @admin.action(description="Mark selected attendance records as Present")
    def mark_present(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, f"{updated} record(s) marked Present.")

    @admin.action(description="Mark selected attendance records as Absent")
    def mark_absent(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, f"{updated} record(s) marked Absent.")

    @admin.action(description="Toggle Present/Absent for selected records")
    def toggle_status(self, request, queryset):
        count = 0
        for rec in queryset:
            rec.status = not rec.status
            rec.save()
            count += 1
        self.message_user(request, f"Toggled status for {count} record(s).")


# ----------
# student profile
 # --------------

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """
    Admin panel for StudentProfile model.
    """

    list_display = ("student_id", "name", "gender", "semester", "division", "marks")
    list_filter = ("division", "semester", "gender")
    search_fields = ("student_id", "name")
    ordering = ("student_id",)

    fieldsets = (
        ("Student Info", {
            "fields": ("student_id", "name", "gender", "semester", "division")
        }),
        ("Performance", {
            "fields": ("marks",)
        }),
    )

# -------------
# time table
# -------------
@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ("semester", "division", "created_at", "timetable_preview")
    list_filter = ("semester", "division", "created_at")
    search_fields = ("semester", "division")
    ordering = ("semester", "division")

    def timetable_preview(self, obj):
        """
        Show a short preview of the timetable JSON in the admin list view.
        """
        try:
            # Convert JSON to pretty string and take first 100 chars
            return json.dumps(obj.data, indent=2)[:100] + "..."
        except Exception:
            return "Invalid JSON"
    timetable_preview.short_description = "Timetable Preview"