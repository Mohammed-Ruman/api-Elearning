from rest_framework import serializers
from main.models import Course, CourseContent,Subscription
from django.contrib.auth import get_user_model

User=get_user_model()

class CourseContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseContent
        fields = ['content_title', 'content_description', 'content']

class CourseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ['teacher', 'students']

class CourseDetailSerializer(serializers.ModelSerializer):
    course_contents = CourseContentSerializer(source='coursecontent_set', many=True, read_only=True)

    class Meta:
        model = Course
        exclude = ['teacher','students','course_price']

class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User 
        fields = ['full_name','email']

    
    def get_full_name(self, obj):
        return obj.name()

class CourseDetailTeacherSerializer(serializers.ModelSerializer):
    course_contents = CourseContentSerializer(source='coursecontent_set', many=True, read_only=True)
    students_purchased = serializers.SerializerMethodField()

    class Meta:
        model = Course
        exclude = ['teacher','students']

    def get_students_purchased(self, obj):
    
        subscriptions = Subscription.objects.filter(course=obj, purchased=True)
        students = [sub.student for sub in subscriptions]
        return StudentSerializer(students, many=True).data



