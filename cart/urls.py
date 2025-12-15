# cart/urls.py
from django.urls import path
from .views import (
    CartDetailView,
    CartItemsListView,
    AddToCartView,
    CartItemDetailView,
    ClearCartView,
    CartSummaryView,
    CartItemCountView
)

urlpatterns = [
    # Cart operations
    path('cart-details/', CartDetailView.as_view(), name='cart-detail'),
    path('summary/', CartSummaryView.as_view(), name='cart-summary'),
    path('count/', CartItemCountView.as_view(), name='cart-count'),
    path('clear/', ClearCartView.as_view(), name='clear-cart'),
    
    # Cart item operations
    path('items/', CartItemsListView.as_view(), name='cart-items-list'),
    path('items/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),
]