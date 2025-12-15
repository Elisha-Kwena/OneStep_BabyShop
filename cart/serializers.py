# cart/serializers.py
from rest_framework import serializers
from .models import Cart, CartItem
from products.serializers import ProductSerializer, ProductVariantSerializer
from django.contrib.auth import get_user_model
from products.models import Product,ProductVariant

User = get_user_model()


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model"""
    product_details = ProductSerializer(source='product', read_only=True)
    variant_details = ProductVariantSerializer(source='variant', read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_name = serializers.CharField(read_only=True)
    product_image = serializers.ImageField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    availability_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'variant', 'quantity', 'size', 'color',
            'product_details', 'variant_details', 'unit_price', 'total_price',
            'product_name', 'product_image', 'is_available', 'availability_status',
            'added_at', 'updated_at'
        ]
        extra_kwargs = {
            'product': {'write_only': True},
            'variant': {'write_only': True},
        }


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    unique_items_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    estimated_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    age_ranges = serializers.ListField(read_only=True)
    genders = serializers.ListField(read_only=True)
    has_gift_items = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'total_items', 'unique_items_count',
            'subtotal', 'estimated_total', 'age_ranges', 'genders',
            'has_gift_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user']


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=True
    )
    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
        required=False
    )
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        required=False,
        allow_null=True
    )
    size = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default=''
    )
    color = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default=''
    )
    
    def validate(self, data):
        """Validate cart item"""
        product = data.get('product')
        variant = data.get('variant')
        quantity = data.get('quantity', 1)
        
        # Check stock availability
        if variant:
            if variant.product != product:
                raise serializers.ValidationError({
                    "variant": "Variant does not belong to the selected product"
                })
            if variant.stock_quantity < quantity:
                raise serializers.ValidationError({
                    "quantity": f"Only {variant.stock_quantity} items available"
                })
        else:
            if product.stock_quantity < quantity:
                raise serializers.ValidationError({
                    "quantity": f"Only {product.stock_quantity} items available"
                })
        
        return data


class UpdateCartItemSerializer(serializers.ModelSerializer):
    """Serializer for updating cart item quantity"""
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def validate_quantity(self, value):
        """Validate quantity"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value