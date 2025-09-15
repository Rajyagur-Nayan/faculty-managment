from django.urls import path
from .views import (
    TimetableView,
)
from .views import UserRegisterView
from .views import UserLoginView
from .views import HolidayUploadView
from . import views
from .views import add_event
from .views import add_event, get_events
from .views import TimetableView
from .views import HolidayListView
from .views import StudentAPIView,AllStudentsAPIView,UpdateAttendanceAPIView,TimetableView, TimetableGetView, TimetableListView,generate_quiz,get_quizzes,GetAttendanceAPIView
from .views import update_marks
from .views import get_student_marks_by_topic

urlpatterns = [

    # register route
    path('auth/register/', UserRegisterView.as_view(), name='user-register'),

    # student role register
    path("students/register/", views.register_student, name="register_student"),
    path('students/<str:student_id>/update-marks/', update_marks, name='update-marks'),
    path("students/<int:student_id>/marks/", views.get_total_marks, name="get_total_marks"),

    #  login routes
        path('auth/login/', UserLoginView.as_view(), name='user-login'),

    #  holiday data 
    path("holidays/upload/", HolidayUploadView.as_view(), name="holiday-upload"),

    #  get holiday
     path('holidays/', HolidayListView.as_view(), name='holiday-list'),

    # gunrate a quize 
    path('generate-quiz/', views.generate_quiz, name='generate_quiz'),

    #  get quiz
    path('api/quiz/', get_quizzes, name='get-quizzes'),

#    progress
    path('marks-by-topic/', get_student_marks_by_topic, name='marks-by-topic'),

    #  add event 
     path('add-event/', add_event, name='add_event'),

    #  fetch the event 
     path('get-events/', get_events, name='get_events'),

    #   attendance route add and get route 
    path('students/', StudentAPIView.as_view(), name='students'),
    path('students/all/', AllStudentsAPIView.as_view(), name='all-students'),
     path('attendance/update/', UpdateAttendanceAPIView.as_view(), name='update-attendance'),
     # GET: Live attendance
    path("attendance/live/", GetAttendanceAPIView.as_view(), name="get-attendance"),

    #  time table 
    path('generate-timetable/', TimetableView.as_view(), name='generate-timetable'),
    path("timetable/", TimetableView.as_view(), name="timetable-generate"),           # POST
    path("timetable/<int:semester>/<str:division>/", TimetableGetView.as_view(), name="timetable-get"),  # GET single
    path("timetables/", TimetableListView.as_view(), name="timetable-list"),


    #  store pdf
    path('upload-pdf/', views.upload_pdf, name='upload_pdf'),
path('get-all-pdfs/', views.get_all_pdfs, name='get_all_pdfs'),
]
