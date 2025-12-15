# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Payment method views
    path('methods/', views.PaymentMethodListView.as_view(), name='payment-method-list'),
    
    # Payment views
    path('', views.PaymentListView.as_view(), name='payment-list'),
    path('create/', views.PaymentCreateView.as_view(), name='payment-create'),
   
    
    # Webhook views
    path('webhook/<str:gateway>/', views.PaymentWebhookView.as_view(), name='payment-webhook'),
    
    # Admin views
    path('admin/payments/', views.AdminPaymentListView.as_view(), name='admin-payment-list'),
    path('admin/payments/<str:payment_reference>/status/', views.PaymentStatusUpdateView.as_view(), name='admin-payment-status-update'),

    # Payment views
    path('<str:payment_reference>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('<str:payment_reference>/verify/', views.PaymentVerifyView.as_view(), name='payment-verify'),
    path('<str:payment_reference>/refund/', views.PaymentRefundView.as_view(), name='payment-refund'),
]