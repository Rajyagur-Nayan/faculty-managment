import pandas as pd
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import  User, Holiday
from .serializers import UserRegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
# For PDF/Excel generation
from rest_framework.parsers import MultiPartParser
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import google.generativeai as genai
from django.http import FileResponse, Http404
from .models import Event
from .serializers import EventSerializer
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .serializers import StudentSerializer
from datetime import datetime
from rest_framework.response import Response
import json
import re
from .models import Quiz
from .serializers import QuizSerializer
from .models import Student, Subject, AttendanceRecord
from .serializers import HolidaySerializer  
import random
from collections import defaultdict
from .models import Timetable
from .serializers import TimetableSerializer, FileUploadSerializer
from django.utils import timezone
from datetime import timedelta
from .models import StudentProfile
from .serializers import StudentProfileSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import PDFDocument
from .serializers import PDFDocumentSerializer
import os


# register route
class UserRegisterView(APIView):
    permission_classes = []  # Anyone can register

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#  login 
class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# Login View
class UserLoginView(APIView):
    permission_classes = []  # anyone can access

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail":"Invalid credentials"}, status=401)

        if not user.check_password(password):
            return Response({"detail":"Invalid credentials"}, status=401)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        })

#  --------------
#  holiday data
# ----------------
class HolidayUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read Excel
            df = pd.read_excel(excel_file)

            # Expected columns: name, date, description
            required_columns = {"name", "date"}
            if not required_columns.issubset(df.columns):
                return Response(
                    {"error": f"Excel must contain these columns: {', '.join(required_columns)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            holidays = []
            for _, row in df.iterrows():
                name = str(row.get("name")).strip()
                date_value = row.get("date")
                description = str(row.get("description")).strip() if "description" in df.columns else ""

                if pd.isna(name) or pd.isna(date_value):
                    continue  # skip incomplete rows

                holidays.append(Holiday(name=name, date=date_value, description=description))

            # Bulk insert
            with transaction.atomic():
                Holiday.objects.bulk_create(holidays, ignore_conflicts=True)

            return Response({"message": f"{len(holidays)} holidays uploaded successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#  get holiday 
class HolidayListView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # only authenticated users can access

    def get(self, request):
        holidays = Holiday.objects.all().order_by('date')
        serializer = HolidaySerializer(holidays, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



# -------------------
#  POST: generate quiz
# -------------------
genai.configure(api_key="AIzaSyDkjTEDNCS11fSej5JtRNpvaZdBRpS8K8I")
@csrf_exempt
@api_view(['POST'])
def generate_quiz(request):
    """
    Generate a quiz via Gemini API for a given topic, level, and semester.
    Stores all questions in the Quiz table and returns them.
    Automatically deletes quizzes older than 1 hour.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    # Delete old quizzes (>1 hour)
    Quiz.objects.filter(created_at__lte=timezone.now() - timedelta(hours=1)).delete()

    # Parse input JSON
    try:
        body = json.loads(request.body.decode("utf-8"))
        topic = body.get("topic", "general knowledge")
        level = body.get("level", "easy")        # optional difficulty
        semester = body.get("semester", "Sem 1") # semester field
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    # Prompt for Gemini
    prompt = f"""
    Generate 5 multiple-choice quiz questions about the topic: '{topic}', level: '{level}'.
    Return ONLY valid JSON, NO explanation or text, NO markdown.
    JSON format MUST be:
    {{
        "quiz": [
            {{
                "question": "string",
                "options": ["string", "string", "string", "string"],
                "answer": "string"
            }},
            ...
        ]
    }}
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        ai_text = response.text.strip()

        # Remove markdown fences if present
        if ai_text.startswith("```"):
            ai_text = re.sub(r"^```[a-zA-Z]*\n", "", ai_text)
            ai_text = re.sub(r"\n```$", "", ai_text)

        quiz_json = json.loads(ai_text)
        quiz_data = quiz_json.get("quiz", [])

        if not quiz_data:
            return JsonResponse({"message": "AI returned empty quiz"}, status=500)

        # Save quizzes using serializer
        saved_quizzes = []
        failed_quizzes = []

        for q in quiz_data:
            options = q.get("options", ["", "", "", ""])
            while len(options) < 4:
                options.append("")

            transformed = {
                "topic": topic,
                "question": q.get("question", ""),
                "option1": options[0],
                "option2": options[1],
                "option3": options[2],
                "option4": options[3],
                "answer": q.get("answer", ""),
                "semester": semester,
            }

            serializer = QuizSerializer(data=transformed)
            if serializer.is_valid():
                serializer.save()
                saved_quizzes.append(serializer.data)
            else:
                failed_quizzes.append({
                    "question": q.get("question", ""),
                    "errors": serializer.errors
                })

        return JsonResponse({
            "message": f"{len(saved_quizzes)} quizzes generated and saved",
            "quizzes": saved_quizzes,
            "failed": failed_quizzes
        })

    except Exception as e:
        return JsonResponse({
            "error": "Failed to generate or parse quiz",
            "details": str(e)
        }, status=500)


# -------------------
#  GET: fetch quizzes
# -------------------
@api_view(['GET'])
@permission_classes([AllowAny])  # ✅ Allow all users
def get_quizzes(request):
    """
    Get quizzes filtered by topic (mandatory).
    Example query: /api/quiz/?topic=math
    Accessible by any user regardless of creator.
    """
    topic = request.GET.get("topic")

    if not topic:
        return Response({
            "status": "error",
            "message": "Please provide a topic as a query parameter, e.g., /api/quiz/?topic=math"
        }, status=400)

    quizzes = Quiz.objects.filter(topic__icontains=topic)

    if not quizzes.exists():
        return Response({
            "status": "success",
            "count": 0,
            "quizzes": [],
            "message": f"No quizzes found for topic '{topic}'"
        })

    serializer = QuizSerializer(quizzes, many=True)
    return Response({
        "status": "success",
        "count": quizzes.count(),
        "quizzes": serializer.data
    })
#  ------
#  event 
# --------

@api_view(['POST'])
def add_event(request):
    """
    Expects JSON body:
    {
        "title": "Meeting",
        "description": "Discuss project",
        "date": "2025-09-12",
        "time": "15:30"
    }
    """
    data = request.data
    try:
        event_datetime = datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
    except ValueError:
        return Response({"error": "Invalid date or time format"}, status=status.HTTP_400_BAD_REQUEST)
    
    event = Event(
        title=data.get('title'),
        description=data.get('description', ''),
        event_datetime=event_datetime
    )
    event.save()
    
    serializer = EventSerializer(event)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

#  fetch event in the database 

@api_view(['GET'])
def get_events(request):
    """
    Returns all events in the database.
    """
    events = Event.objects.all().order_by('event_datetime')
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)

# find the Average

@api_view(["GET", "POST"])
def get_student_marks_by_topic(request):
    """
    Returns all students' marks grouped by quiz topic and semester,
    with the average marks for each topic.

    GET query params:
      ?semester=<semester_name>
      ?topic=<topic_name>  (optional)

    POST JSON body:
    {
      "semester": "Sem 2",
      "topic": "Data Structures"  (optional)
    }
    """
    # Safely get filters
    if request.method == "GET":
        semester_filter = request.GET.get("semester")
        topic_filter = request.GET.get("topic")
    else:  # POST
        semester_filter = request.data.get("semester")
        topic_filter = request.data.get("topic")

    if not semester_filter:
        return Response({
            "status": "error",
            "message": "Semester is required",
            "data": {}
        }, status=400)

    # Filter quizzes by semester (required) and topic (optional)
    quizzes = Quiz.objects.filter(semester__iexact=semester_filter)
    if topic_filter:
        quizzes = quizzes.filter(topic__icontains=topic_filter)

    if not quizzes.exists():
        return Response({
            "status": "success",
            "message": f"No quizzes found for semester '{semester_filter}'",
            "data": {}
        })

    # Prepare data grouped by semester -> topic
    result = {}
    for quiz in quizzes:
        topic = quiz.topic

        # Replace this with actual relation if marks are linked to quiz
        students_marks = StudentProfile.objects.all().values("student_id", "name", "marks")
        marks_list = [s["marks"] for s in students_marks]

        avg_marks = sum(marks_list) / len(marks_list) if marks_list else 0

        if semester_filter not in result:
            result[semester_filter] = {}

        result[semester_filter][topic] = {
            "students": list(students_marks),
            "average_marks": avg_marks
        }

    return Response({
        "status": "success",
        "data": result
    })

# -------------
#  time table
# ------------

# Constants
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
SLOTS = ['09:00-09:45', '09:45-10:30', '10:30-11:15', '11:15-12:00', '13:00-13:45', '13:45-14:30']
DIVISIONS = ['A', 'B']  # Each semester has 2 divisions


class TimetableView(APIView):
    """
    POST: Upload Excel -> Generate timetable -> Save into DB
    """

    def post(self, request):
        # --- 1. Validate File ---
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        excel_file = serializer.validated_data["file"]
        try:
            df = pd.read_excel(excel_file, engine='openpyxl')
        except Exception:
            return Response({"status": "error", "message": "Invalid Excel file."}, status=status.HTTP_400_BAD_REQUEST)

        # --- 2. Validate Columns ---
        expected_cols = ["Teacher_Name", "Semester", "Subject_Name", "Hours_Per_Week", "Type"]
        if not all(col in df.columns for col in expected_cols):
            return Response(
                {"status": "error", "message": f"Excel must contain columns: {expected_cols}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 3. Initialize Timetable ---
        timetable = {}
        for sem in df["Semester"].unique():
            for div in DIVISIONS:
                class_name = f"Semester {sem} - Division {div}"
                timetable[class_name] = {day: {slot: None for slot in SLOTS} for day in DAYS}

        # --- 4. Track Teacher Availability ---
        teacher_availability = defaultdict(lambda: {day: {slot: True for slot in SLOTS} for day in DAYS})

        # --- 5. Place Free Slots First ---
        for class_name in timetable:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                day = random.choice(DAYS)
                idx = random.randint(0, len(SLOTS) - 2)
                slot1 = SLOTS[idx]
                slot2 = SLOTS[idx + 1]
                if timetable[class_name][day][slot1] is None and timetable[class_name][day][slot2] is None:
                    timetable[class_name][day][slot1] = {"subject": "FREE", "teacher": "N/A"}
                    timetable[class_name][day][slot2] = {"subject": "FREE", "teacher": "N/A"}
                    placed = True
                attempts += 1
            if not placed:
                return Response(
                    {"error": f"Could not place consecutive free periods for {class_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # --- 6. Prepare Subjects List ---
        subjects_list = []
        for _, row in df.iterrows():
            sem = row["Semester"]
            subj_name = row["Subject_Name"]
            teacher = row["Teacher_Name"]
            hours = int(row["Hours_Per_Week"])
            subj_type = row.get("Type", "lecture").lower()  # 'lecture' or 'lab'

            # Add for both divisions
            for div in DIVISIONS:
                subjects_list.append({
                    "class": f"Semester {sem} - Division {div}",
                    "subject": subj_name,
                    "teacher": teacher,
                    "hours": hours,
                    "type": subj_type,
                })

        random.shuffle(subjects_list)  # randomize for fairness

        # --- 7. Scheduling Algorithm ---
        for subj in subjects_list:
            hours_remaining = subj["hours"]
            class_name = subj["class"]
            teacher = subj["teacher"]
            subj_type = subj["type"]

            while hours_remaining > 0:
                placed = False
                days_random = random.sample(DAYS, len(DAYS))
                for day in days_random:
                    if subj_type == "lab":
                        # Find 2 consecutive empty slots
                        for i in range(len(SLOTS) - 1):
                            slot1 = SLOTS[i]
                            slot2 = SLOTS[i + 1]
                            if (timetable[class_name][day][slot1] is None and
                                timetable[class_name][day][slot2] is None and
                                teacher_availability[teacher][day][slot1] and
                                teacher_availability[teacher][day][slot2]):
                                timetable[class_name][day][slot1] = {"subject": subj["subject"], "teacher": teacher}
                                timetable[class_name][day][slot2] = {"subject": subj["subject"], "teacher": teacher}
                                teacher_availability[teacher][day][slot1] = False
                                teacher_availability[teacher][day][slot2] = False
                                hours_remaining -= 2
                                placed = True
                                break
                        if placed:
                            break
                    else:  # lecture
                        for slot in SLOTS:
                            if timetable[class_name][day][slot] is None and teacher_availability[teacher][day][slot]:
                                timetable[class_name][day][slot] = {"subject": subj["subject"], "teacher": teacher}
                                teacher_availability[teacher][day][slot] = False
                                hours_remaining -= 1
                                placed = True
                                break
                        if placed:
                            break
                if not placed:
                    return Response(
                        {"error": f"Could not schedule {subj['subject']} for {class_name} with teacher {teacher}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # --- 8. Save Timetable in DB (Semester + Division) ---
        for class_name, days in timetable.items():
            sem_part = class_name.split(" - ")[0]  # "Semester 1"
            div_part = class_name.split(" - ")[1]  # "Division A"
            semester = int(sem_part.replace("Semester", "").strip())
            division = div_part.replace("Division", "").strip()

            Timetable.objects.update_or_create(
                semester=semester,
                division=division,
                defaults={"data": days},
            )

        return Response({"status": "success", "data": timetable}, status=status.HTTP_200_OK)


class TimetableGetView(APIView):
    """
    GET: Get timetable for a specific semester + division
    """

    def get(self, request, semester, division):
        try:
            timetable = Timetable.objects.get(semester=semester, division=division.upper())
            serializer = TimetableSerializer(timetable)
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        except Timetable.DoesNotExist:
            return Response({"status": "error", "message": "No timetable found"}, status=status.HTTP_404_NOT_FOUND)


class TimetableListView(APIView):
    """
    GET: Get all timetables (all semesters & divisions)
    """

    def get(self, request):
        timetables = Timetable.objects.all()
        serializer = TimetableSerializer(timetables, many=True)
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
# -----------------
#  attendance data
# -----------------

class StudentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Upload Excel and create/update students
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(file)
            required_columns = ['Enrollment_No', 'Student_Name', 'Gender', 'Semester', 'Division']
            if not all(col in df.columns for col in required_columns):
                return Response({"error": f"Excel must contain columns: {required_columns}"}, status=status.HTTP_400_BAD_REQUEST)
            
            created_students = []
            for _, row in df.iterrows():
                student, created = Student.objects.update_or_create(
                    student_id=row['Enrollment_No'],
                    defaults={
                        'name': row['Student_Name'],
                        'gender': row['Gender'],
                        'semester': row['Semester'],
                        'division': row['Division']
                    }
                )
                created_students.append(StudentSerializer(student).data)

            return Response({
                "message": f"{len(created_students)} students uploaded successfully",
                "students": created_students
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Get students by semester
    def get(self, request):
        sem = request.query_params.get('semester')
        if not sem:
            return Response({"error": "Semester parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        students = Student.objects.filter(semester=sem)
        serializer = StudentSerializer(students, many=True)
        return Response({"students": serializer.data})

# get all the student 
class AllStudentsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        students = Student.objects.all()  # Get all students
        serializer = StudentSerializer(students, many=True)
        return Response({"students": serializer.data})

# update the attendance table 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from datetime import datetime
from .models import Student, Subject, AttendanceRecord  # adjust your imports

class UpdateAttendanceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # only logged-in users (teachers)

    def put(self, request):
        """
        Update attendance for students filtered by semester and subject.
        Expected JSON body:
        {
            "semester": 2,
            "subject_id": 3,
            "date": "2025-09-13",
            "updates": [
                {"student_id": "ENR002", "status": true},
                {"student_id": "ENR005", "status": false}
            ]
        }
        """
        semester = request.data.get('semester')
        subject_id = request.data.get('subject_id')
        date_str = request.data.get('date')
        updates = request.data.get('updates', [])

        if not semester or not subject_id or not date_str:
            return Response(
                {"error": "semester, subject_id, and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        subject = get_object_or_404(Subject, id=subject_id)

        # Optional: only allow the teacher of the subject to update
        # if hasattr(subject, 'teacher') and subject.teacher.user != request.user:
        #     return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Get all students for this semester
        students_in_sem = Student.objects.filter(semester=semester)
        student_ids_in_sem = [s.student_id for s in students_in_sem]

        failed_updates = []

        for item in updates:
            student_id = item.get('student_id')

            # Validate status
            status_val = item.get('status')
            if status_val is None:
                failed_updates.append({
                    "student_id": student_id,
                    "error": "Missing status (must be true or false)"
                })
                continue

            # Ensure it is boolean
            status_val = bool(status_val)

            if student_id not in student_ids_in_sem:
                failed_updates.append({"student_id": student_id, "error": "Student not in this semester"})
                continue

            student = get_object_or_404(Student, student_id=student_id)

            # Create or update attendance
            AttendanceRecord.objects.update_or_create(
                student=student,
                subject=subject,
                date=date,
                defaults={'status': status_val}
            )

        return Response({
            "message": "Attendance updated successfully",
            "failed": failed_updates
        })
# ----------------------------
#  get live attendance data 
# -----------------------------

class GetAttendanceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # only logged-in teachers

    def get(self, request):
        """
        Get live attendance for students in a semester and subject.
        Query params: ?semester=2&subject_id=3&date=2025-09-13

        Response:
        {
            "semester": 2,
            "subject": "Maths",
            "date": "2025-09-13",
            "students": [
                {"student_id": "ENR002", "name": "Alice", "status": "P"},
                {"student_id": "ENR005", "name": "Bob", "status": "A"},
                {"student_id": "ENR010", "name": "Charlie", "status": "Not Marked"}
            ]
        }
        """
        semester = request.query_params.get('semester')
        subject_id = request.query_params.get('subject_id')
        date_str = request.query_params.get('date')

        if not semester or not subject_id or not date_str:
            return Response(
                {"error": "semester, subject_id, and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        subject = get_object_or_404(Subject, id=subject_id)

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Get all students in this semester
        students = Student.objects.filter(semester=semester)

        response_data = []
        for student in students:
            # Check if attendance exists
            record = AttendanceRecord.objects.filter(
                student=student,
                subject=subject,
                date=date
            ).first()

            if record:
                status_display = "P" if record.status else "A"
            else:
                status_display = "Not Marked"

            response_data.append({
                "student_id": student.student_id,
                "name": student.name,
                "status": status_display
            })

        return Response({
            "semester": semester,
            "subject": subject.name,
            "date": date_str,
            "students": response_data
        })


# ---------------
#  student data
# --------------

# ✅ Register a student
@api_view(["POST"])
def register_student(request):
    """
    Register a student with division (A or B).
    Body example:
    {
        "user_id": 1,
        "name": "John Doe",
        "division": "A"
    }
    """
    serializer = StudentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "student": serializer.data})
    return Response({"status": "error", "errors": serializer.errors}, status=400)


# ✅ Register a student
@api_view(["POST"])
def register_student(request):
    """
    Register a student with division (A or B).
    Body example:
    {
        "user_id": 1,
        "name": "John Doe",
        "division": "A"
    }
    """
    serializer = StudentProfileSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "student": serializer.data})
    return Response({"status": "error", "errors": serializer.errors}, status=400)

# ✅ Update student marks
@api_view(["PUT"])
def update_marks(request, student_id):
    """
    Update quiz marks for a student.
    Body example:
    {
        "marks": 10
    }
    """
    student = get_object_or_404(StudentProfile, student_id=student_id)
    marks = request.data.get("marks")

    try:
        marks = int(marks)
    except (TypeError, ValueError):
        return Response({"error": "Marks must be an integer"}, status=400)

    student.marks += marks  # Add marks to existing total
    student.save()

    return Response({
        "status": "success",
        "student": StudentProfileSerializer(student).data
    })

# ✅ Get total marks for a student
@api_view(["GET"])
def get_total_marks(request, student_id):
    """
    Get total quiz marks of a student.
    Example: GET /api/students/1/marks/
    """
    student = get_object_or_404(StudentProfile, id=student_id)
    return Response({
        "status": "success",
        "student": student.name,
        "division": student.division,
        "total_marks": student.marks
    })



# --------------
# store the pdf
# --------------

@api_view(['POST'])
def upload_pdf(request):
    serializer = PDFDocumentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_pdfs(request):
    pdfs = PDFDocument.objects.all().order_by('-uploaded_at')  # latest first

    # Optional: if a specific PDF download is requested
    pdf_id = request.query_params.get('download')  # e.g., /api/get-all-pdfs/?download=1
    if pdf_id:
        try:
            pdf = PDFDocument.objects.get(pk=pdf_id)
            file_path = pdf.file.path
            if os.path.exists(file_path):
                response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
                return response
            else:
                raise Http404("File not found")
        except PDFDocument.DoesNotExist:
            raise Http404("PDF not found")

    # Default: return JSON list
    serializer = PDFDocumentSerializer(pdfs, many=True)
    return Response(serializer.data)