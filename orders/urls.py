from django.urls import path
from .views import (
    OrderListView, OrderCreateView, OrderDetailView, OrderUpdateView, 
    OrderCancelView, OrderStatusUpdateView, OrderPaymentUpdateView, 
    OrderItemListView, OrderTrackView, OrderSummaryView, 
    MonthlyOrderStatsView, CheckoutView, TestCheckoutView, 
    AdminOrderListView
)

urlpatterns = [
    # Fixed paths (specific) should come FIRST
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    
    # Dashboard & analytics views (FIXED PATHS - MUST COME BEFORE CATCH-ALL)
    path('summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('stats/monthly/', MonthlyOrderStatsView.as_view(), name='monthly-stats'),
    
    # Checkout views (FIXED PATHS)
    path('checkout/', CheckoutView.as_view(), name='checkout'),

    # Admin views (FIXED PATHS)
    path('admin/orders/', AdminOrderListView.as_view(), name='admin-order-list'),
    
    # Dynamic paths (with parameters) should come LAST
    path('<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_number>/update/', OrderUpdateView.as_view(), name='order-update'),
    path('<str:order_number>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('<str:order_number>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<str:order_number>/payment/', OrderPaymentUpdateView.as_view(), name='order-payment-update'),
    path('<str:order_number>/items/', OrderItemListView.as_view(), name='order-item-list'),
    path('<str:order_number>/track/', OrderTrackView.as_view(), name='order-track'),
]