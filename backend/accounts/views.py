from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .models import UserProfile
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from django.utils import timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    logger.info(f"Registration attempt with data: {request.data}")
    
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            logger.info(f"User {user.username} registered successfully")
            return Response({
                'message': 'User registered successfully',
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                'token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return Response({
                'message': 'Registration failed due to server error',
                'errors': {'server': ['An unexpected error occurred. Please try again.']}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Format validation errors for better frontend handling
    logger.warning(f"Registration validation failed: {serializer.errors}")
    
    # Create a more user-friendly error message
    error_messages = []
    detailed_errors = {}
    
    for field, errors in serializer.errors.items():
        detailed_errors[field] = errors
        if field == 'username':
            if 'already exists' in str(errors).lower():
                error_messages.append('Username is already taken. Please choose a different one.')
            else:
                error_messages.append(f'Username: {", ".join(errors)}')
        elif field == 'email':
            if 'already exists' in str(errors).lower():
                error_messages.append('Email is already registered. Please use a different email.')
            else:
                error_messages.append(f'Email: {", ".join(errors)}')
        elif field == 'password':
            error_messages.append(f'Password: {", ".join(errors)}')
        elif field == 'password2':
            error_messages.append(f'Password confirmation: {", ".join(errors)}')
        elif field == 'non_field_errors':
            error_messages.extend(errors)
        else:
            error_messages.append(f'{field.replace("_", " ").title()}: {", ".join(errors)}')
    
    return Response({
        'message': 'Registration failed. Please check the errors below.',
        'errors': detailed_errors,
        'error_summary': error_messages
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    logger.info(f"Login attempt for username: {request.data.get('username', 'N/A')}")
    
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        
        if user:
            if not user.is_active:
                logger.warning(f"Inactive user {username} attempted login")
                return Response({
                    'message': 'Account is inactive. Please contact support.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            refresh = RefreshToken.for_user(user)
            logger.info(f"User {username} logged in successfully")
            return Response({
                'message': 'Login successful',
                'is_admin': user.is_staff or user.is_superuser,
                'token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        
        logger.warning(f"Failed login attempt for username: {username}")
        return Response({
            'message': 'Invalid username or password. Please try again.'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    logger.warning(f"Login validation failed: {serializer.errors}")
    return Response({
        'message': 'Please provide valid username and password.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user's profile data"""
    user = request.user
    try:
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_verified': getattr(user.profile, 'is_verified', False),
            'verification_date': user.profile.verification_date.strftime('%Y-%m-%d %H:%M:%S') if user.profile.verification_date else None,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
        }
        return Response(profile_data)
    except Exception as e:
        logger.error(f"Error fetching user profile for {user.username}: {str(e)}")
        return Response(
            {'error': 'Error fetching user profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_users(request):
    """Get all users with their verification status"""
    try:
        users = User.objects.all()
        user_data = []
        
        for user in users:
            try:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'is_verified': getattr(user.profile, 'is_verified', False),
                    'verification_date': user.profile.verification_date.strftime('%Y-%m-%d %H:%M:%S') if user.profile.verification_date else None,
                    'verified_by': user.profile.verified_by.username if user.profile.verified_by else None,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
                })
            except Exception as e:
                logger.error(f"Error processing user {user.username}: {str(e)}")
                continue
        
        return Response(user_data)
    except Exception as e:
        logger.error(f"Error in get_all_users: {str(e)}")
        return Response(
            {'error': 'An error occurred while fetching users'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def verify_user(request, user_id):
    """Verify or reject a user"""
    try:
        user = User.objects.get(id=user_id)
        action = request.data.get('action')
        
        if action == 'verify':
            user.profile.is_verified = True
            user.profile.verification_date = timezone.now()
            user.profile.verified_by = request.user
            user.profile.save()
            logger.info(f"User {user.username} verified by {request.user.username}")
            return Response({'message': f'User {user.username} has been verified'})
        elif action == 'reject':
            user.profile.is_verified = False
            user.profile.verification_date = None
            user.profile.verified_by = None
            user.profile.save()
            logger.info(f"User {user.username} rejected by {request.user.username}")
            return Response({'message': f'User {user.username} has been rejected'})
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
            
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in verify_user: {str(e)}")
        return Response({'error': 'An error occurred while updating user status'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
