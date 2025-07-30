from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

router = DefaultRouter()
# Add your viewsets here when you create them
# router.register(r'stocks', views.StockViewSet)
router.register(r'trades', views.TradeViewSet, basename='trade')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register_user, name='register'),
    path('fetch-trades/', views.TradeListCreateView.as_view(), name='trade-list'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/chart-data/', views.ChartDataView.as_view(), name='dashboard-chart-data'),
    path('dashboard/pie-data/', views.PieDataView.as_view(), name='dashboard-pie-data'),
    path('user-positions/', views.user_positions, name='user_positions'),
    path('trades/', views.TradeListView.as_view(), name='trade-list'),
    path('trades/stats/', views.trade_stats, name='trade-stats'),
    path('trades/symbols/', views.stock_symbols, name='stock-symbols'),
]
