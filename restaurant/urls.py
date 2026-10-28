from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    InventoryItemViewSet,
    MenuItemViewSet,
    RestaurantTableViewSet,
    ReservationViewSet,
    OrderViewSet,
    DailySalesReportView,
    StockAlertsReportView,
    TopSellingReportView,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'inventory', InventoryItemViewSet, basename='inventory')
router.register(r'menu', MenuItemViewSet, basename='menu')
router.register(r'tables', RestaurantTableViewSet, basename='table')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    # Reports
    path('reports/daily-sales/', DailySalesReportView.as_view(), name='report-daily-sales'),
    path('reports/stock-alerts/', StockAlertsReportView.as_view(), name='report-stock-alerts'),
    path('reports/top-selling/', TopSellingReportView.as_view(), name='report-top-selling'),
]
