# cart/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Cart, CartItem
from .serializers import (
    CartSerializer, CartItemSerializer,
    AddToCartSerializer, UpdateCartItemSerializer
)

User = get_user_model()


class CartMixin:
    """Mixin to get or create user's cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_cart(self):
        """Get or create cart for current user"""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


class CartDetailView(CartMixin, generics.RetrieveAPIView):
    """
    Retrieve current user's cart details
    GET /api/cart/
    
    Returns: Full cart object with items and totals
    """
    serializer_class = CartSerializer
    
    def get_object(self):
        return self.get_cart()


class CartItemsListView(CartMixin, generics.ListAPIView):
    """
    List all items in user's cart
    GET /api/cart/items/
    
    Returns: Array of cart item objects
    """
    serializer_class = CartItemSerializer
    
    def get_queryset(self):
        cart = self.get_cart()
        return cart.items.all()


class AddToCartView(CartMixin, generics.CreateAPIView):
    """
    Add item to cart
    POST /api/cart/items/add/
    
    Body: {product, quantity, variant, size, color}
    Returns: Success status, updated cart, and new item
    """
    serializer_class = AddToCartSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = self.get_cart()
        
        # Add item to cart
        item = cart.add_item(
            product=serializer.validated_data['product'],
            quantity=serializer.validated_data.get('quantity', 1),
            variant=serializer.validated_data.get('variant'),
            size=serializer.validated_data.get('size', ''),
            color=serializer.validated_data.get('color', '')
        )
        
        # Return JSON response
        cart_serializer = CartSerializer(cart, context={'request': request})
        item_serializer = CartItemSerializer(item, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Item added to cart successfully.',
            'cart': cart_serializer.data,
            'item': item_serializer.data
        }, status=status.HTTP_200_OK)


class CartItemDetailView(CartMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a cart item
    GET /api/cart/items/{id}/ - Get item details
    PUT/PATCH /api/cart/items/{id}/ - Update item quantity
    DELETE /api/cart/items/{id}/ - Remove item from cart
    
    Returns: JSON with success status and updated data
    """
    serializer_class = UpdateCartItemSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'item_id'
    
    def get_queryset(self):
        cart = self.get_cart()
        return cart.items.all()
    
    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, id=self.kwargs['item_id'])
        self.check_object_permissions(self.request, obj)
        return obj
    
    def update(self, request, *args, **kwargs):
        """Update cart item quantity"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update item
        self.perform_update(serializer)
        
        # Get updated cart
        cart = self.get_cart()
        cart_serializer = CartSerializer(cart, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Item quantity updated successfully.',
            'cart': cart_serializer.data,
            'item': CartItemSerializer(instance, context={'request': request}).data
        })
    
    def perform_destroy(self, instance):
        """Remove item from cart"""
        cart = self.get_cart()
        cart.remove_item(instance.id)
    
    def destroy(self, request, *args, **kwargs):
        """Remove item from cart"""
        instance = self.get_object()
        self.perform_destroy(instance)
        
        # Get updated cart
        cart = self.get_cart()
        cart_serializer = CartSerializer(cart, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Item removed from cart successfully.',
            'cart': cart_serializer.data
        }, status=status.HTTP_200_OK)


class ClearCartView(CartMixin, generics.DestroyAPIView):
    """
    Clear all items from cart
    DELETE /api/cart/clear/
    
    Returns: JSON with success status and empty cart
    """
    
    def get_object(self):
        return self.get_cart()
    
    def destroy(self, request, *args, **kwargs):
        cart = self.get_object()
        cart.clear()
        
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'success': True,
            'message': 'Cart cleared successfully.',
            'cart': cart_serializer.data
        }, status=status.HTTP_200_OK)


class CartSummaryView(CartMixin, generics.RetrieveAPIView):
    """
    Get cart summary for quick display
    GET /api/cart/summary/
    
    Returns: Lightweight cart summary
    """
    
    def get_object(self):
        return self.get_cart()
    
    def retrieve(self, request, *args, **kwargs):
        cart = self.get_object()
        
        return Response({
            'success': True,
            'summary': cart.get_cart_summary()
        }, status=status.HTTP_200_OK)


class CartItemCountView(CartMixin, generics.RetrieveAPIView):
    """
    Get cart item counts for badge/header
    GET /api/cart/count/
    
    Returns: Only total and unique item counts
    """
    serializer_class = CartSerializer
    
    def get_object(self):
        return self.get_cart()
    
    def retrieve(self, request, *args, **kwargs):
        cart = self.get_object()
        
        return Response({
            'success': True,
            'total_items': cart.total_items,
            'unique_items': cart.unique_items_count
        }, status=status.HTTP_200_OK)