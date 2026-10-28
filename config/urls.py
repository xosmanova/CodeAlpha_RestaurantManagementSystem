"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root_overview(request):
    return JsonResponse({
        "project": "Restaurant Management System API",
        "internship": "CodeAlpha Backend Development Internship",
        "task": "TASK 3: Restaurant Management System",
        "version": "1.0.0",
        "endpoints": {
            "admin_panel": "/admin/",
            "api_root": "/api/",
            "menu_items": "/api/menu/",
            "categories": "/api/categories/",
            "tables": "/api/tables/",
            "table_availability": "/api/tables/available/?date=YYYY-MM-DD&time=HH:MM&party_size=2",
            "reservations": "/api/reservations/",
            "orders": "/api/orders/",
            "inventory": "/api/inventory/",
            "inventory_low_stock": "/api/inventory/low_stock/",
            "reports_daily_sales": "/api/reports/daily-sales/",
            "reports_stock_alerts": "/api/reports/stock-alerts/",
            "reports_top_selling": "/api/reports/top-selling/",
        }
    })


urlpatterns = [
    path('', api_root_overview, name='api-overview'),
    path('admin/', admin.site.urls),
    path('api/', include('restaurant.urls')),
]
