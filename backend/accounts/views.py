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

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'User registered successfully',
            'user': serializer.data,
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'is_admin': user.is_staff or user.is_superuser,
                'token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response({
            'message': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                print(f"Error processing user {user.username}: {str(e)}")
                continue
        
        return Response(user_data)
    except Exception as e:
        print(f"Error in get_all_users: {str(e)}")
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
            return Response({'message': f'User {user.username} has been verified'})
        elif action == 'reject':
            user.profile.is_verified = False
            user.profile.verification_date = None
            user.profile.verified_by = None
            user.profile.save()
            return Response({'message': f'User {user.username} has been rejected'})
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
            
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
