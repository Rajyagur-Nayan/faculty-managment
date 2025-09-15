from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db import models
import uuid

class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_FACULTY = 'faculty'
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_FACULTY, 'Faculty'),
        (ROLE_STUDENT, 'Student'),
    ]

    email = models.EmailField(unique=True)  # ← add this
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    USERNAME_FIELD = 'email'       # Use email to log in
    REQUIRED_FIELDS = ['username']  # username is still required for AbstractUser

    # add extra fields if needed (phone, emp_id)

# --------------
#  student data
#  -------------


class StudentProfile(models.Model):
    student_id = models.CharField(
        max_length=50,
        unique=True,
        default="TEMP-ID"  # ✅ simple default value
    )
    name = models.CharField(max_length=255, default="Unknown")
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        default="Male"
    )
    semester = models.PositiveSmallIntegerField(default=1)
    division = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B")],
        default="A"
    )
    marks = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.student_id} - {self.name}"
# -----------
#  quiz store
# -----------
class Quiz(models.Model):
    topic = models.CharField(max_length=255)
    question = models.TextField()
    option1 = models.CharField(max_length=255, default="N/A")
    option2 = models.CharField(max_length=255, default="N/A")
    option3 = models.CharField(max_length=255, default="N/A")
    option4 = models.CharField(max_length=255, default="N/A")
    answer = models.CharField(max_length=255, default="N/A")
    semester = models.CharField(max_length=20,default="N/A")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

#  holiday model 
class Holiday(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.date}"
    

#  event model 
class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    event_datetime = models.DateTimeField()

    def __str__(self):
        return self.title

# -----------
#  time table 
# -----------

class Timetable(models.Model):
    semester = models.IntegerField()
    division = models.CharField(max_length=5)  # A or B
    data = models.JSONField()  # Store full timetable for that semester+division
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("semester", "division")

    def __str__(self):
        return f"Semester {self.semester} - Division {self.division}"

# ---------------------
#  teacher and subject
# ----------------------
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)  # FK to Teacher
    semester = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"
    
# ------------------
#  attendance tale 
# ------------------

class Student(models.Model):
    student_id = models.CharField(max_length=20, primary_key=True)  # e.g., Enrollment No.
    name = models.CharField(max_length=255)
    semester = models.PositiveSmallIntegerField()
    division = models.CharField(max_length=5)
    gender = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.student_id} - {self.name}"

class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.BooleanField(default=False)  # True = Present, False = Absent

    class Meta:
        unique_together = ('student', 'subject', 'date')

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.date} - {'P' if self.status else 'A'}"

# ----------
# pdf store
# ----------
# myapp/models.py
from django.db import models

class PDFDocument(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title