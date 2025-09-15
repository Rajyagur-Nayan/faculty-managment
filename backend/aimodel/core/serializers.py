from rest_framework import serializers
from .models import User
from .models import Holiday
from .models import Event
from .models import Student, Subject, AttendanceRecord
from django.db.models import Count
from .models import Quiz,Timetable,StudentProfile

from .models import PDFDocument

#  pdf
class PDFDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFDocument
        fields = ['id', 'title', 'file', 'uploaded_at']

class UserRegisterSerializer(serializers.ModelSerializer):
    # Extra fields for student
    roll_no = serializers.CharField(required=False, allow_blank=True)
    semester_id = serializers.IntegerField(required=False)
    batch = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'roll_no', 'semester_id', 'batch']

    def create(self, validated_data):
        role = validated_data.get('role', 'student')
        password = validated_data.pop('password')
        roll_no = validated_data.pop('roll_no', None)
        semester_id = validated_data.pop('semester_id', None)
        batch = validated_data.pop('batch', None)

        user = User(**validated_data)
        user.set_password(password)
        user.save()

# If role is student, create StudentProfile
        if role == 'student':
            semester = None
            if semester_id:
                from .models import Semester
                try:
                    semester = Semester.objects.get(id=semester_id)
                except Semester.DoesNotExist:
                    semester = None
        return user

#  holiday
class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'

#  event 
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'event_datetime']
        
    class FileUploadSerializer(serializers.Serializer):
        file = serializers.FileField()


#  time table 

class TimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timetable
        fields = ["id", "semester", "division", "data", "created_at"]




class FileUploadSerializer(serializers.Serializer):
    """
    Serializer to validate the uploaded Excel file.
    It ensures that a file is present in the request.
    """
    file = serializers.FileField()

    class Meta:
        fields = ('file',)

#  attendance 

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ['student', 'student_name', 'subject', 'date', 'status']


class AttendancePercentageSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    percentage = serializers.FloatField()

    #  quiz 
class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = '__all__'

        #  get holiday
class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date', 'description']

        # student data 
class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = "__all__"