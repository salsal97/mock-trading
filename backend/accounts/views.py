from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import UserProfile
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from django.utils import timezone
from decimal import Decimal, ROUND_UP
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
        # Get or create profile if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('1000.00')}
        )
        
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_verified': profile.is_verified,
            'balance': float(profile.balance),
            'verification_date': profile.verification_date.strftime('%Y-%m-%d %H:%M:%S') if profile.verification_date else None,
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
    """Get all users with their verification status and balances"""
    try:
        users = User.objects.all().order_by('-date_joined')
        user_data = []
        
        for user in users:
            try:
                # Get or create profile if it doesn't exist
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'balance': Decimal('1000.00')}
                )
                
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'is_verified': profile.is_verified,
                    'balance': float(profile.balance),
                    'verification_date': profile.verification_date.strftime('%Y-%m-%d %H:%M:%S') if profile.verification_date else None,
                    'verified_by': profile.verified_by.username if profile.verified_by else None,
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
        
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('1000.00')}
        )
        
        if action == 'verify':
            profile.is_verified = True
            profile.verification_date = timezone.now()
            profile.verified_by = request.user
            profile.save()
            logger.info(f"User {user.username} verified by {request.user.username}")
            return Response({'message': f'User {user.username} has been verified'})
        elif action == 'reject':
            profile.is_verified = False
            profile.verification_date = None
            profile.verified_by = None
            profile.save()
            logger.info(f"User {user.username} verification rejected by {request.user.username}")
            return Response({'message': f'User {user.username} verification has been rejected'})
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in verify_user: {str(e)}")
        return Response(
            {'error': 'An error occurred while updating user'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_user_balances(request):
    """Get all user balances with trade statistics (admin only)"""
    try:
        users = User.objects.all().order_by('-profile__balance')
        balance_data = []
        
        for user in users:
            # Get or create profile if it doesn't exist
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'balance': Decimal('1000.00')}
            )
            
            # Get trade statistics
            total_trades = user.trades.count()
            settled_trades = user.trades.filter(is_settled=True).count()
            total_pnl = sum(trade.profit_loss or Decimal('0.00') for trade in user.trades.filter(is_settled=True))
            
            # Get market maker statistics
            mm_markets = user.market_maker_markets.count()
            
            user_balance_data = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'balance': float(profile.balance),
                'is_verified': profile.is_verified,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'total_trades': total_trades,
                'settled_trades': settled_trades,
                'total_pnl': float(total_pnl),
                'market_maker_markets': mm_markets,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_updated': profile.updated_at.isoformat() if profile.updated_at else None
            }
            balance_data.append(user_balance_data)
        
        return Response({
            'users': balance_data,
            'total_users': len(balance_data),
            'total_balance': sum(data['balance'] for data in balance_data),
            'verified_users': len([data for data in balance_data if data['is_verified']]),
            'active_traders': len([data for data in balance_data if data['total_trades'] > 0])
        })
        
    except Exception as e:
        logger.error(f"Error fetching user balances: {str(e)}")
        return Response({
            'error': f'Failed to fetch user balances: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_adjust_balance(request, user_id):
    """Manually adjust user balance (admin only)"""
    try:
        user = get_object_or_404(User, id=user_id)
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('1000.00')}
        )
        
        action = request.data.get('action')  # 'set' or 'adjust'
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'Admin adjustment')
        
        if not amount:
            return Response({
                'error': 'Amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_UP)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_balance = profile.balance
        
        if action == 'set':
            # Set absolute balance
            profile.balance = amount
        elif action == 'adjust':
            # Add/subtract from current balance
            profile.balance += amount
        else:
            return Response({
                'error': 'Invalid action. Use "set" or "adjust"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Round to 2 decimal places
        profile.balance = profile.balance.quantize(Decimal('0.01'), rounding=ROUND_UP)
        profile.save()
        
        # Log the balance adjustment
        logger.info(f"Admin {request.user.username} adjusted balance for {user.username}: "
                   f"{old_balance} -> {profile.balance} (action: {action}, amount: {amount}, reason: {reason})")
        
        return Response({
            'success': True,
            'message': f'Balance updated for {user.username}',
            'old_balance': float(old_balance),
            'new_balance': float(profile.balance),
            'adjustment': float(amount) if action == 'adjust' else float(profile.balance - old_balance),
            'action': action,
            'reason': reason
        })
        
    except Exception as e:
        logger.error(f"Error adjusting user balance: {str(e)}")
        return Response({
            'error': f'Failed to adjust balance: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_balance_history(request, user_id):
    """Get balance change history for a user (admin only)"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Get settlement history from trades
        settled_trades = user.trades.filter(is_settled=True).order_by('-settled_at')
        
        balance_history = []
        
        for trade in settled_trades:
            balance_history.append({
                'date': trade.settled_at.isoformat() if trade.settled_at else None,
                'type': 'settlement',
                'description': f'Market settlement: {trade.market.premise[:50]}...',
                'amount': float(trade.profit_loss or 0),
                'market_id': trade.market.id,
                'trade_id': trade.id
            })
        
        # Sort by date descending
        balance_history.sort(key=lambda x: x['date'] or '', reverse=True)
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'current_balance': float(user.profile.balance),
            'history': balance_history,
            'total_settlements': len(balance_history)
        })
        
    except Exception as e:
        logger.error(f"Error fetching balance history: {str(e)}")
        return Response({
            'error': f'Failed to fetch balance history: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
