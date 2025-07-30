from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from rest_framework.parsers import MultiPartParser,JSONParser
from decimal import Decimal, InvalidOperation
from decimal import Decimal, InvalidOperation
from datetime import datetime
from rest_framework import generics, permissions, views
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import TruncMonth
from .models import Trade
from .serializers import TradeSerializer
from datetime import datetime
import re
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
import requests
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db.models import Sum, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import io
from .models import Trade
from .serializers import TradeSerializer



@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint
    """
    return Response({
        'status': 'healthy',
        'message': 'Stock Calculator API is running'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Validation
        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, username):
            return Response({
                'error': 'Invalid email format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'User already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(username=username, password=password)
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'User registered successfully',
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class TradeViewSet(viewsets.ModelViewSet):
    """Trade ViewSet for listing, creating, and bulk uploading trades."""
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def get_queryset(self):
        """Return trades belonging to the authenticated user only."""
        return Trade.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Assign the current user when creating a trade."""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a single trade, return data in array form."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trade = serializer.save(user=request.user)
        return Response({"data": [serializer.data]}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='bulk_upload')
    def bulk_upload(self, request, *args, **kwargs):
        """Accept plain, clean CSV and create trades in bulk reliably."""
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = uploaded_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded_file))
            required_columns = {'stock_symbol', 'action', 'quantity', 'price_per_share', 'date', 'notes'}

            actual_headers = {h.strip().lower() for h in reader.fieldnames}
            missing_columns = required_columns - actual_headers
            if missing_columns:
                return Response({
                    "detail": f"Missing required columns: {', '.join(missing_columns)}",
                    "found_headers": ", ".join(actual_headers)
                }, status=status.HTTP_400_BAD_REQUEST)

            trades = []
            for i, raw_row in enumerate(reader, start=2):  # starting at line 2
                row = {
                    (k.strip().lower()): v.strip() if v is not None else ""
                    for k, v in raw_row.items()
                }

                quantity = row.get('quantity')
                price_per_share = row.get('price_per_share')
                date_value = row.get('date')

                if not quantity or not price_per_share:
                    return Response({
                        "detail": f"Missing quantity or price_per_share at line {i}"
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    quantity = Decimal(quantity)
                    price_per_share = Decimal(price_per_share)
                except InvalidOperation:
                    return Response({
                        "detail": f"Invalid decimal value at line {i}."
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    parsed_date = datetime.strptime(date_value, "%Y-%m-%d").date()
                except ValueError:
                    return Response({
                        "detail": f"Invalid date format at line {i}. Use YYYY-MM-DD."
                    }, status=status.HTTP_400_BAD_REQUEST)

                trades.append(Trade(
                    user=request.user,
                    stock_symbol=row.get('stock_symbol'),
                    action=row.get('action'),
                    quantity=quantity,
                    price_per_share=price_per_share,
                    date=parsed_date,
                    notes=row.get('notes'),
                ))

            Trade.objects.bulk_create(trades)

            created_trades = Trade.objects.filter(user=request.user).order_by("-date")[:len(trades)]
            serializer = TradeSerializer(created_trades, many=True)

            return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        




class TradeListCreateView(generics.ListCreateAPIView):
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        return Trade.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DashboardStatsView(views.APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        trades = Trade.objects.filter(user=request.user)

        total_investment = sum(
            (t.quantity * t.price_per_share) if t.action == 'buy' else 0
            for t in trades
        )
        total_sales = sum(
            (t.quantity * t.price_per_share) if t.action == 'sell' else 0
            for t in trades
        )
        current_value = total_investment + (total_sales - total_investment)  # Rough approximation
        total_profit = total_sales - total_investment
        profit_percentage = (total_profit / total_investment * 100) if total_investment > 0 else 0

        data = {
            "totalInvestment": total_investment,
            "currentValue": current_value,
            "totalProfit": total_profit,
            "profitPercentage": profit_percentage,
        }
        return Response(data)


class ChartDataView(views.APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        trades = Trade.objects.filter(user=request.user)

        # Group by month
        chart_data = []
        grouped = trades.annotate(month=TruncMonth('date')).values('month')
        months = sorted(set([t.date.strftime("%Y-%m") for t in trades]))
        total_investment = 0
        total_profit = 0
        for month in months:
            date_obj = datetime.strptime(month, "%Y-%m")
            month_trades = trades.filter(date__year=date_obj.year, date__month=date_obj.month)
            invested = sum((t.quantity * t.price_per_share) for t in month_trades if t.action == 'buy')
            sold = sum((t.quantity * t.price_per_share) for t in month_trades if t.action == 'sell')
            total_investment += invested
            total_profit += sold - invested
            chart_data.append({
                "date": date_obj.strftime("%b"),
                "portfolio": total_investment + total_profit,
                "profit": total_profit
            })

        return Response(chart_data)

class PieDataView(views.APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        trades = Trade.objects.filter(user=request.user)

        allocation = {}
        for t in trades:
            if t.action == 'buy':
                allocation[t.stock_symbol] = allocation.get(t.stock_symbol, 0) + t.quantity
            else:  # sell
                allocation[t.stock_symbol] = allocation.get(t.stock_symbol, 0) - t.quantity

        # Keep only positions > 0
        allocation = {symbol: qty for symbol, qty in allocation.items() if qty > 0}

        total_quantity = sum(allocation.values())

        pie_data = []
        if total_quantity > 0:
            for symbol, quantity in allocation.items():
                percentage = round((quantity / total_quantity) * 100, 2)
                pie_data.append({
                    "name": symbol,
                    "value": percentage,
                })

        return Response(pie_data)
    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_positions(request):
    """
    Get user's current stock positions for auto-population in recovery calculator
    """
    user = request.user
    trades = Trade.objects.filter(user=user)
    
    if not trades.exists():
        return Response({
            'positions': [],
            'message': 'No trades found'
        })
    
    # Calculate net position for each stock
    stock_positions = {}
    
    for trade in trades:
        symbol = trade.stock_symbol
        if symbol not in stock_positions:
            stock_positions[symbol] = {
                 'symbol': symbol,
                  'total_quantity': Decimal('0'),
                  'total_invested': Decimal('0'),
                  'current_quantity': Decimal('0'),
                  'avg_price': Decimal('0'),
                  'latest_price': trade.price_per_share,
                 'latest_trade_id': trade.id,
                 'trades_count': 0
                }

        
        position = stock_positions[symbol]
        position['trades_count'] += 1
        
        if trade.id > position['latest_trade_id']:
         position['latest_price'] = trade.price_per_share
         position['latest_trade_id'] = trade.id
        
        if trade.action == 'buy':
            # Add to position
            old_qty = position['current_quantity']
            old_invested = position['total_invested']
            
            new_qty = old_qty + trade.quantity
            new_invested = old_invested + (trade.quantity * trade.price_per_share)
            
            position['current_quantity'] = new_qty
            position['total_invested'] = new_invested
            position['total_quantity'] += trade.quantity
            
            # Recalculate average price
            if new_qty > 0:
                position['avg_price'] = new_invested / new_qty
                
        else:  # sell
            # Reduce position
            position['current_quantity'] -= trade.quantity
            # Note: We don't adjust total_invested for sells to maintain avg_price calculation
    
    # Filter only positions with current holdings and calculate P&L
    active_positions = []
    for symbol, position in stock_positions.items():
        if position['current_quantity'] > 0:
            current_value = position['current_quantity'] * position['latest_price']
            invested_value = position['current_quantity'] * position['avg_price']
            unrealized_pnl = current_value - invested_value
            unrealized_loss = max(0, invested_value - current_value)  # Only loss amount
            
            active_positions.append({
                'symbol': symbol,
                'quantity': float(position['current_quantity']),
                'avg_price': float(position['avg_price']),
                'current_price': float(position['latest_price']),
                'current_value': float(current_value),
                'invested_value': float(invested_value),
                'unrealized_pnl': float(unrealized_pnl),
                'unrealized_loss': float(unrealized_loss),
                'pnl_percentage': float((unrealized_pnl / invested_value) * 100) if invested_value > 0 else 0,
                'trades_count': position['trades_count']
            })
    
    # Sort by unrealized loss (descending) to show biggest losers first
    active_positions.sort(key=lambda x: x['unrealized_loss'], reverse=True)
    
    return Response({
        'positions': active_positions,
        'total_positions': len(active_positions)
    })


class TradePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class TradeListView(generics.ListAPIView):
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TradePagination
    
    def get_queryset(self):
        queryset = Trade.objects.filter(user=self.request.user).order_by('-date', 'id')
        # ... your filtering logic
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Check if client wants all data
        if request.query_params.get('all') == 'true':
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def trade_stats(request):
    """
    Get trade statistics for the authenticated user
    """
    trades = Trade.objects.filter(user=request.user)
    
    buy_trades = trades.filter(action='buy')
    sell_trades = trades.filter(action='sell')
    
    total_trades = trades.count()
    total_buy_trades = buy_trades.count()
    total_sell_trades = sell_trades.count()
    
    # Calculate total investment and returns
    total_bought = sum(trade.quantity * trade.price_per_share for trade in buy_trades)
    total_sold = sum(trade.quantity * trade.price_per_share for trade in sell_trades)
    
    unique_stocks = trades.values_list('stock_symbol', flat=True).distinct().count()
    
    stats = {
        'total_trades': total_trades,
        'total_buy_trades': total_buy_trades,
        'total_sell_trades': total_sell_trades,
        'total_invested': round(float(total_bought), 2),
        'total_returns': round(float(total_sold), 2),
        'net_position': round(float(total_sold - total_bought), 2),
        'unique_stocks': unique_stocks,
    }
    
    return Response(stats)


@api_view(['GET'])
def stock_symbols(request):
    """
    Get unique stock symbols for the authenticated user
    """
    symbols = Trade.objects.filter(
        user=request.user
    ).values_list('stock_symbol', flat=True).distinct().order_by('stock_symbol')
    
    return Response(list(symbols))