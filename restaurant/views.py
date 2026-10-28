from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_date, parse_time
from datetime import datetime

from .models import (
    Category,
    InventoryItem,
    MenuItem,
    RestaurantTable,
    Reservation,
    Order,
)
from .serializers import (
    CategorySerializer,
    InventoryItemSerializer,
    MenuItemSerializer,
    RestaurantTableSerializer,
    ReservationSerializer,
    OrderSerializer,
    OrderCreateSerializer,
)
from .services import OrderService, TableService, ReportService


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        alerts = ReportService.get_stock_alerts()
        return Response(alerts)


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related('category').prefetch_related('ingredients__inventory_item').all()
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category_id = self.request.query_params.get('category')
        available = self.request.query_params.get('available')
        if category_id:
            qs = qs.filter(category_id=category_id)
        if available is not None:
            is_avail = available.lower() in ['true', '1']
            qs = qs.filter(is_available=is_avail)
        return qs


class RestaurantTableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Check table availability:
        Query params: date=YYYY-MM-DD, time=HH:MM, party_size=int, duration=int
        """
        date_str = request.query_params.get('date')
        time_str = request.query_params.get('time')
        party_size = int(request.query_params.get('party_size', 2))
        duration = int(request.query_params.get('duration', 120))

        if not date_str or not time_str:
            return Response(
                {"error": "Please provide 'date' (YYYY-MM-DD) and 'time' (HH:MM) parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_date = parse_date(date_str)
        target_time = parse_time(time_str)

        if not target_date or not target_time:
            return Response(
                {"error": "Invalid date or time format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        available_tables = TableService.get_available_tables(
            target_date=target_date,
            target_time=target_time,
            party_size=party_size,
            duration_minutes=duration
        )
        serializer = self.get_serializer(available_tables, many=True)
        return Response({
            'date': str(target_date),
            'time': str(target_time),
            'party_size': party_size,
            'duration_minutes': duration,
            'available_count': len(available_tables),
            'tables': serializer.data
        })


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related('table').all()
    serializer_class = ReservationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date_filter = self.request.query_params.get('date')
        table_id = self.request.query_params.get('table')
        status_filter = self.request.query_params.get('status')

        if date_filter:
            qs = qs.filter(reservation_date=date_filter)
        if table_id:
            qs = qs.filter(table_id=table_id)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('table').prefetch_related('items__menu_item').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status', '').upper()
        valid_statuses = [s[0] for s in Order.STATUS_CHOICES]

        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status '{new_status}'. Valid choices: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status == 'CANCELLED':
            OrderService.cancel_order(order)
        else:
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
            if new_status == 'COMPLETED' and order.table:
                # Check if other active orders exist on this table
                active_exist = Order.objects.filter(
                    table=order.table,
                    status__in=['PENDING', 'PREPARING']
                ).exclude(pk=order.pk).exists()
                if not active_exist:
                    order.table.status = 'AVAILABLE'
                    order.table.save(update_fields=['status'])

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        OrderService.cancel_order(order)
        return Response({
            "message": f"Order {order.order_number} cancelled and ingredients restocked.",
            "order": OrderSerializer(order).data
        })


class DailySalesReportView(APIView):
    def get(self, request):
        date_param = request.query_params.get('date')
        try:
            report = ReportService.get_daily_sales(target_date=date_param)
            return Response(report)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockAlertsReportView(APIView):
    def get(self, request):
        alerts = ReportService.get_stock_alerts()
        return Response({
            "total_low_stock_items": len(alerts),
            "alerts": alerts
        })


class TopSellingReportView(APIView):
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        top_items = ReportService.get_top_selling_items(limit=limit)
        return Response(top_items)
