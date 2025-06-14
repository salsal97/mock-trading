from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from .models import Market, SpreadBid
from .serializers import (
    MarketSerializer, MarketCreateSerializer, MarketUpdateSerializer,
    SpreadBidSerializer, SpreadBidCreateSerializer
)

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to create/edit markets.
    Regular authenticated users can only read.
    """
    def has_permission(self, request, view):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin users
        return request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

class MarketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing markets.
    - GET operations: Available to all authenticated users
    - POST/PUT/PATCH/DELETE operations: Admin users only
    """
    queryset = Market.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MarketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MarketUpdateSerializer
        return MarketSerializer
    
    def get_queryset(self):
        """Filter markets based on query parameters"""
        queryset = Market.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by active trading
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status='OPEN')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user when creating a market"""
        serializer.save(created_by=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add business logic"""
        market = self.get_object()
        
        # Only allow deletion of markets that haven't started trading
        if market.status not in ['CREATED']:
            return Response(
                {'error': 'Cannot delete markets that have started trading'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def settle(self, request, pk=None):
        """Settle a market with outcome (admin only)"""
        market = self.get_object()
        
        if not market.can_be_settled:
            return Response(
                {'error': 'Market cannot be settled at this time'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        outcome = request.data.get('outcome')
        if outcome is None:
            return Response(
                {'error': 'Outcome is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            outcome = int(outcome)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Outcome must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        market.status = 'SETTLED'
        market.outcome = outcome
        market.save()
        
        serializer = MarketSerializer(market)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def stats(self, request):
        """Get market statistics for admin dashboard"""
        total_markets = Market.objects.count()
        markets_by_status = {}
        
        for status_choice in Market.STATUS_CHOICES:
            status_key = status_choice[0]
            count = Market.objects.filter(status=status_key).count()
            markets_by_status[status_key] = count
        
        active_trading = Market.objects.filter(status='OPEN').count()
        
        stats = {
            'total_markets': total_markets,
            'markets_by_status': markets_by_status,
            'active_trading': active_trading,
            'recent_markets': MarketSerializer(
                Market.objects.order_by('-created_at')[:5], 
                many=True
            ).data
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def spread_bids(self, request, pk=None):
        """Get all spread bids for a market"""
        market = self.get_object()
        bids = market.spread_bids.all().order_by('bid_time')
        serializer = SpreadBidSerializer(bids, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def place_spread_bid(self, request, pk=None):
        """Place a spread bid on a market"""
        market = self.get_object()
        
        # Add market to request data
        data = request.data.copy()
        data['market'] = market.id
        
        serializer = SpreadBidCreateSerializer(
            data=data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            bid = serializer.save()
            response_serializer = SpreadBidSerializer(bid)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SpreadBidViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing spread bids.
    Only read operations are allowed - bids are created through MarketViewSet.
    """
    queryset = SpreadBid.objects.all()
    serializer_class = SpreadBidSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter spread bids based on query parameters"""
        queryset = SpreadBid.objects.all()
        
        # Filter by market if provided
        market_id = self.request.query_params.get('market')
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset.order_by('bid_time')
