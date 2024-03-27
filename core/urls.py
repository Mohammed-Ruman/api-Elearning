
from django.contrib import admin
from django.urls import path
from main import views
from main.views import RegisterAPIView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.home_page,name='home'),
    path('register/',RegisterAPIView.as_view(),name='register'),
    path('verify-user/',views.registration_otp_verification,name='verify user'),
    path('login/',views.login_page,name='login'),
    path('login/verify',views.verify_otp_login,name='login verify'),
    path('check/',views.check_auth,name='check'),
    path('teacher/dashboard',views.teacher_dashboard,name='teacher dashboard'),
    path('teacher/addcourse',views.add_course,name='add course'),
    path('teacher/editcourse',views.edit_course,name='edit course'),
    path('teacher/deletecourse',views.delete_course,name='delete course'),
    path('teacher/topic/add',views.add_topic,name='add topic'),
    path('teacher/topic/delete',views.delete_topic,name='delete topic'),
    path('course/',views.course_page,name='course'),
    path('payment/paypal/', views.paypal_payment_view, name='paypal_payment'),
    path('payment/<uuid:id>/',views.payment_page,name='payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_failure, name='payment_failure'),
    path('student/dashboard/', views.student_dashboard, name='student dashboard'),
]
