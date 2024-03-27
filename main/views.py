
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.decorators import api_view, APIView,permission_classes, authentication_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .email import send_otp_via_email, send_otp
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Course,CourseContent,Subscription
from .serializer import CourseListSerializer,CourseDetailSerializer, CourseDetailTeacherSerializer
import random
from django.db.models import Sum, F
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from accounts.serializer import UserSerializer
from .email import send_otp_via_email
from .permissions import HasCoursePermissions, HasCourseContentPermissions

from rest_framework.views import APIView
import paypalrestsdk
from django.shortcuts import redirect
from django.core.mail import send_mail

User=get_user_model()

@api_view()
def home_page(request):
    return Response({
        'isError' : False,
        'status' : 200
    })


class RegisterAPIView(APIView):
    def post(self,request):
        try:
            data=request.data
            type_ = data.pop('registration_type')
            if type_ is None :
                raise ValueError('registration_type is empty')
            if type_!='teacher' and type_!='student':
                raise ValueError('registration_type is invalid')
            serializer = UserSerializer(data=data)
            if serializer.is_valid():
                email_ = serializer.validated_data['email']
                first_name_ = serializer.validated_data['first_name']
                last_name_ = serializer.validated_data['last_name']
                password_ = serializer.validated_data['password']

                user = User.objects.filter(email=email_)

                if user.exists():
                    if user.first().is_verified:
                        return Response({"error": "Email Already Exists"},  status = status.HTTP_400_BAD_REQUEST)
                    else:
                        send_otp_via_email(email_)
                        return Response({"message": "OTP sent for email verification"}, status=status.HTTP_200_OK)

                user = User.objects.create(
                    email=email_,
                    first_name=first_name_,
                    last_name=last_name_
                )

                if type_ == 'teacher':
                    user.is_teacher = True
                    group, created = Group.objects.get_or_create(name="Teacher")
                    user.groups.add(group)
                elif type_ == 'student':
                    user.is_student = True
                    group, created = Group.objects.get_or_create(name="Student")
                    user.groups.add(group)

                user.set_password(password_)
                user.save()
                send_otp_via_email(email_)
                return Response({"message": "Registration Successful! Check Email for Account Activation"},
                                status= status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'message' : str(e)},
                status=status.HTTP_400_BAD_REQUEST)

@api_view(['post'])
def registration_otp_verification(request):
    try:
        if request.method=="POST":
            data = request.data
            email = data.get('email')
            otp = data.get('otp')
            if email is None or otp is None:
                raise ValueError('Email or OTP is empty')

            user = get_object_or_404(User, email=email)
            if otp==user.otp:
                user.is_verified=True
                user.save()
                return Response({
                    'message':'Email Verified Successfully'},status=status.HTTP_200_OK)
            else :
                raise ValueError('Invalid or Wrong OTP')

    except Exception as e:
        return Response({
            'message':str(e)
        },status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_page(request):
    try:
        if request.method != 'POST':
            return Response({"error": "Method Not Allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        data = request.data
        email = data.get('email')
        password = data.get('password')
        print(email)

        if email is None or password is None:
            raise ValueError('Email or Password is empty')

        user_obj = User.objects.filter(email=email)

        if not user_obj.exists():
            return Response({"error": "Invalid Email"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(email=email, password=password)

        if user is not None:
            if user.is_verified:
                otp = random.randint(100000, 999999)
                send_otp(otp, email)
                user.otp = otp
                user.save()
                return Response({"message": "OTP sent for email verification"}, status=status.HTTP_200_OK)
            send_otp_via_email(email)
            return Response({"error": "Account is not activated. Kindly Verify your email"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            'message':str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def verify_otp_login(request):
    try:
        if request.method=="POST":
            data = request.data
            email = data.get('email')
            otp = data.get('otp')
            if email is None or otp is None:
                raise ValueError('Email or OTP is empty')

            user = get_object_or_404(User, email=email)
            if otp==user.otp:
                token, created = Token.objects.get_or_create(user=user)
                return Response({"token": token.key}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Method Not Allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


    except Exception as e:
        return Response({
            'message':str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def check_auth(request):
    return Response('You are authenticated')

@api_view(['GET'])
@permission_classes([IsAuthenticated, HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def teacher_dashboard(request):
    try:
        courses = Course.objects.filter(teacher=request.user)
        for course in courses:
            print(course)
        student_set = set()
        sub = Subscription.objects.filter(course__in=courses, purchased=True)
        for sup in sub:
            student_set.add(sup.student)

        total_students = Subscription.objects.filter(course__in=courses, purchased=True).count()
        total_income = Subscription.objects.filter(course__in=courses, purchased=True).aggregate(total_income=Sum(F('course__course_price')))

        serializer = CourseDetailTeacherSerializer(courses, many=True)
        return Response({'total_course':len(courses), 'total_students': total_students,'total_income': total_income['total_income'],'courses': serializer.data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)



@api_view(['POST'])
@permission_classes([IsAuthenticated , HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def add_course(request):
    try:
        if request.method == 'POST':
            title = request.data.get('title')
            description = request.data.get('description')
            course_price = request.data.get('course_price')
            cover_image = request.FILES.get('cover_image')

        
            if(title is None or description is None or course_price is None or cover_image is None ):
                raise ValueError("All Fields are Mandatory")

            # Create a new Course object with the uploaded file
            course = Course.objects.create(
                title=title,
                description=description,
                course_price=course_price,
                cover_image=cover_image,
                teacher=request.user
            )

            index = 0
            while True:
                title = request.POST.get(f'contents[{index}][content_title]')
                if title is None:
                    break
                description = request.POST.get(f'contents[{index}][content_description]')
                content_file = request.FILES.get(f'contents[{index}][content]')
                CourseContent.objects.create(
                    course=course,
                    content_title=title,
                    content_description=description,
                    content=content_file
                )
                index += 1
            return Response({'message': 'Course added successfully'}, status=status.HTTP_201_CREATED)
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    except Exception as e:
        return Response({
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['PUT'])
@permission_classes([IsAuthenticated, HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def edit_course(request):
    try:
        if request.method == 'PUT':
            course_id = request.data.get('course_id')
            title = request.data.get('title')
            description = request.data.get('description')
            course_price = request.data.get('course_price')
            cover_image = request.FILES.get('cover_image')

            if not all([course_id, title, description, course_price]):
                raise ValueError("All Fields are Mandatory")

            course = Course.objects.get(uuid=course_id, teacher=request.user)

            course.title = title
            course.description = description
            course.course_price = course_price

            if cover_image:
                course.cover_image = cover_image
            course.save()

            # Update course contents
            index = 0
            while True:
                content_id = request.data.get(f'contents[{index}][content_id]')
                if content_id is None:
                    break
                content_title = request.data.get(f'contents[{index}][content_title]')
                content_description = request.data.get(f'contents[{index}][content_description]')
                content_file = request.FILES.get(f'contents[{index}][content]')
                
                if content_id:
                    content = CourseContent.objects.get(pk=content_id)
                    content.content_title = content_title
                    content.content_description = content_description
                    if content_file:
                        content.content = content_file
                    content.save()
                else:
                    CourseContent.objects.create(
                        course=course,
                        content_title=content_title,
                        content_description=content_description,
                        content=content_file
                    )
                index += 1
            
            serialized_course = CourseDetailSerializer(course).data

            return Response({'message': 'Course updated successfully','course':serialized_course}, status=status.HTTP_200_OK)
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    except ObjectDoesNotExist:
        return Response({'message': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def delete_course(request):
    try:
        if request.method == 'DELETE':
            course_id = request.data.get('course_id')

            course = Course.objects.get(uuid=course_id, teacher=request.user)
            course.delete()

            return Response({'message': 'Course Deleted successfully'}, status=status.HTTP_200_OK)
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    except ObjectDoesNotExist:
        return Response({'message': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e :
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated , HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def add_topic(request):
    try:
        if request.method == 'POST':
            course_id = request.data.get('course_id')
            course = Course.objects.get(uuid=course_id, teacher=request.user)
            students=Subscription.objects.filter(course=course,purchased=True)
            index = 0
            while True:
                title = request.POST.get(f'contents[{index}][content_title]')
                if title is None:
                    break
                description = request.POST.get(f'contents[{index}][content_description]')
                content_file = request.FILES.get(f'contents[{index}][content]')
                CourseContent.objects.create(
                    course=course,
                    content_title=title,
                    content_description=description,
                    content=content_file
                )
                index += 1
            ser_course = CourseDetailSerializer(course)

            subject = 'New Topic Added!'
            for student in students:
                html_message = f'Dear E-Learner, a new topic has been added to the course. <strong>{course.title}</strong>'
                send_mail(subject, "", settings.EMAIL_HOST, [student.student.email], html_message=html_message, fail_silently=False)
            return Response({'message': 'Topic added successfully','course':ser_course.data}, status=status.HTTP_201_CREATED)
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    except ObjectDoesNotExist:
        return Response({'message': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e :
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated , HasCoursePermissions])
@authentication_classes([TokenAuthentication])
def delete_topic(request):
    try:
        if request.method == 'DELETE':
            content_id = request.data.get('content_id')
            content = CourseContent.objects.get(uuid=content_id)
            content.delete()
            return Response({'message': 'Topic deleted successfully'}, status=status.HTTP_201_CREATED)
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    except ObjectDoesNotExist:
        return Response({'message': 'Content not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e :
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    


@api_view(['GET', 'POST'])
def course_page(request):
    if request.method == 'GET':
        courses = Course.objects.all()
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        search = request.data.get('search')
        courses = Course.objects.filter(title__icontains=search)
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    return Response({'message': 'Method not allowed'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def paypal_payment_view(request):
    try:
        course_id = request.GET.get('course_id')
        user_email = request.GET.get('user_id')
        course = Course.objects.get(uuid=course_id)
        user = User.objects.filter(email=user_email).first()
        sub = Subscription.objects.create(        
            course=course,
            student=user
            )
        # Initialize PayPal SDK
        paypalrestsdk.configure({
            'mode': settings.PAYPAL_MODE,
            'client_id': settings.PAYPAL_CLIENT_ID,
            'client_secret': settings.PAYPAL_CLIENT_SECRET,
        })

        

        payment = paypalrestsdk.Payment({
            'intent': 'sale',
            'payer': {
                'payment_method': 'paypal'
            },
            'redirect_urls': {
                'return_url': f'http://localhost:8000/payment/success/?sub_id={sub.uuid}',
                'cancel_url': f'http://localhost:8000/payment/cancel/?sub_id={sub.uuid}'
            },
            'transactions': [{
                'amount': {
                    'total': str(course.course_price),
                    'currency': 'USD'
                },
                'description': course.title
            }]
        })

        if payment.create():
            # Redirect user to PayPal for payment
            for link in payment.links:
                if link.method == 'REDIRECT':
                    return Response({'message':'Complete Payment','payment_link': link.href})
        else:
            return Response(payment.error, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    


@api_view(['GET'])
@permission_classes([IsAuthenticated, HasCourseContentPermissions])
@authentication_classes([TokenAuthentication])
def payment_page(request, id):
    course = Course.objects.get(uuid=id)
    host = request.get_host()

    if request.method == 'GET':
        redirect_url = 'http://{0}//payment/paypal/?course_id={1}&user_id={2}'.format(
            host, course.uuid, request.user)
        return redirect(redirect_url)
    

@api_view(['GET'])
def payment_success(request):
    sub_id=request.GET.get('sub_id')
    subscrip=Subscription.objects.get(uuid=sub_id)
    subscrip.purchased=True
    subscrip.save()
    return Response({'message':'Payment Success'})

@api_view(['GET'])
def payment_failure(request):
    sub_id=request.GET.get('sub_id')
    subscrip=Subscription.objects.get(uuid=sub_id)
    subscrip.purchased=False
    subscrip.save()
    return Response({'message':'Payment Failed'})

@api_view(['GET'])
@permission_classes([IsAuthenticated, HasCourseContentPermissions])
@authentication_classes([TokenAuthentication])
def student_dashboard(request):
    try:
        sub=Subscription.objects.filter(student=request.user, purchased=True)
        print(sub)
        courses = [s.course for s in sub]
        for c in courses:
            print(c)
        serialized_course = CourseDetailSerializer(courses, many=True).data
        return Response({'courses':serialized_course})

    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    

