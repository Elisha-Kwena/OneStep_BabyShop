from rest_framework import serializers
from .models import (
    Product,
    ProductImage,
    RecentlyViewed,
    Category,
    Brand,
    ProductVariant,
    Wishlist,
    Tag,
    ProductReview
)

from babyshop_backend.base_serializers import BaseUserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name','slug','description','image','parent','is_active','created_at','updated_at']
        read_only_fields = ['slug','created_at','updated_at']



class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id','name','slug','description','logo','is_active']

        read_only_fields = ['slug']

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = ProductImage
        fields = ['product','image','image_url','id','alt_text','is_primary','order']
        read_only_fields = ['product']

    def get_image_url(self, obj):
        if obj.image:
            try:
                return obj.image.url
            except ValueError:
                return None
        return None

class ProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id','product','size','color','color_code','product_code','stock_quantity','price_adjustment','is_active','current_price','in_stock']
        read_only_fields = ['product_code']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, allow_null=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['slug', 'created_at', 'updated_at', 'availability_status', 'product_code']
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
            'short_description': {'required': False},
            'age_range': {'required': False},
            'category': {'required': False},
            'gender': {'required': False, 'default': 'unisex'},
            'season': {'required': False, 'default': 'all_season'},
        }
    
    def update(self, instance, validated_data):
        """Handle partial updates"""
        # Update only the fields that are provided
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Save will handle slug generation and availability_status
        instance.save()
        return instance



class ProductReviewSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    # Product information
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    
    # Computed fields
    average_rating = serializers.SerializerMethodField()
    days_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'product_slug', 'user',
            'rating', 'title', 'comment', 'fit_rating', 'quality_rating',
            'is_verified_purchase', 'helpful_count', 'average_rating',
            'days_ago', 'is_approved', 'is_active', 'created_at', 'updated_at'  # Add is_active
        ]
        read_only_fields = [
            'user', 'product_name', 'product_slug', 'average_rating',
            'days_ago', 'is_verified_purchase', 'helpful_count',
            'is_approved', 'is_active', 'created_at', 'updated_at'  # Add is_active
        ]

        extra_kwargs = {
            'fit_rating': {'required': False},
            'quality_rating': {'required': False},
        }
    
    def get_average_rating(self, obj):
        """Use the model's property"""
        return obj.average_rating
    
    def get_days_ago(self, obj):
        """Calculate how many days ago the review was created"""
        from django.utils.timezone import now
        delta = now() - obj.created_at
        return delta.days
    
    def validate(self, data):
        """Ensure a user can only review once per product"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            product = data.get('product') or (self.instance.product if self.instance else None)
            
            # Check if creating new review (not updating existing)
            if self.instance is None and product:
                if ProductReview.objects.filter(user=user, product=product, is_active=True).exists():
                    raise serializers.ValidationError(
                        "You have already reviewed this product."
                    )
        
        return data


class TagSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    recent_products = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'products', 'product_count', 'recent_products']
        read_only_fields = ['slug']
    
    def get_recent_products(self, obj):
        """Get 3 most recent active products with this tag"""
        recent_products = obj.products.filter(
            is_active=True
        ).order_by('-created_at')[:3]
        return ProductListSerializer(recent_products, many=True).data
    
    def to_representation(self, instance):
        """Custom representation to avoid huge product lists"""
        representation = super().to_representation(instance)
        
        # Remove full products list if it's too large (optional)
        if 'products' in representation and isinstance(representation['products'], list):
            # Instead of full product objects, just show count
            # Or keep minimal info
            representation['products'] = [
                {'id': p.id, 'name': p.name, 'slug': p.slug} 
                for p in instance.products.all()[:5]  # Limit to 5
            ]
        
        return representation

class WishlistSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    # Product details
    products_detail = ProductSerializer(source='products', many=True, read_only=True)
    
    # For adding products via API
    product_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        required=False,
        source='products'
    )
    
    # Wishlist stats
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'user', 'name', 'products', 'products_detail', 'product_ids',
            'product_count', 'total_value', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True}
        }
    
    def get_total_value(self, obj):
        """Calculate total price of all products in wishlist"""
        total = sum(product.price for product in obj.products.all() if product.price)
        return total
    
    def validate_product_ids(self, value):
        """Ensure products are active"""
        inactive_products = [p for p in value if not p.is_active]
        if inactive_products:
            names = [p.name for p in inactive_products]
            raise serializers.ValidationError(
                f"The following products are not active: {', '.join(names)}"
            )
        return value
    
    def create(self, validated_data):
        """Handle wishlist creation with optional name"""
        user = self.context['request'].user
        
        # Check if user already has a wishlist (if not allowing multiple)
        # If you want only one wishlist per user:
        if Wishlist.objects.filter(user=user).exists() and not validated_data.get('name'):
            raise serializers.ValidationError(
                "You already have a wishlist. Use the add-product endpoint instead."
            )
        
        return super().create(validated_data)


class RecentlyViewedSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    # Product information
    product_detail = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = RecentlyViewed
        fields = ['id', 'user', 'product', 'product_detail', 'viewed_at']
        read_only_fields = ['user', 'viewed_at']

# Additional specialized serializers
class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'product_code', 'short_description',
                 'price', 'compare_at_price', 'discount_percentage',
                 'category_name', 'brand_name', 'primary_image',
                 'gender', 'age_range', 'is_featured', 'in_stock']
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            try:
                # safely get url
                return primary_image.image.url
            except ValueError:
                # image field exists but no file is associated
                return None
        return None

class ProductDetailSerializer(ProductSerializer):
    """Extended serializer for product detail view"""
    tags = TagSerializer(many=True, read_only=True)
    related_products = serializers.SerializerMethodField()
    review_stats = serializers.SerializerMethodField()
    
    class Meta(ProductSerializer.Meta):
        fields = [
            'id', 'name', 'slug', 'product_code', 'description', 'short_description',
            'price', 'compare_at_price', 'category', 'brand', 'gender', 'age_range',
            'stock_quantity', 'is_featured', 'is_bestseller', 'is_active',
            'created_at', 'updated_at', 'availability_status',
            'category_name', 'brand_name', 'discount_percentage', 
            'in_stock', 'low_stock', 'images', 'variants',
            'tags', 'related_products', 'review_stats'
        ]
    
    def get_related_products(self, obj):
        # Get products in same category, excluding current product
        related = Product.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id)[:4]
        return ProductListSerializer(related, many=True).data
    
    def get_review_stats(self, obj):
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
            return {
                'average_rating': avg_rating,
                'total_reviews': reviews.count(),
                'rating_distribution': {
                    '5_star': reviews.filter(rating=5).count(),
                    '4_star': reviews.filter(rating=4).count(),
                    '3_star': reviews.filter(rating=3).count(),
                    '2_star': reviews.filter(rating=2).count(),
                    '1_star': reviews.filter(rating=1).count(),
                }
            }
        return None

class CategoryDetailSerializer(CategorySerializer):
    """Extended serializer with product counts"""
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    children = CategorySerializer(many=True, read_only=True)
    products = serializers.SerializerMethodField()
    
    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['product_count', 'children','products']

    def get_product_count(self,obj):
        if hasattr(obj, '_active_products'):
            return obj._active_products.count()
        return obj.products.filter(is_active=True).count()
    
    def get_products(self, obj):
        # Use the prefetched active products
        if hasattr(obj, '_active_products'):
            products = obj._active_products
        else:
            products = obj.products.filter(is_active=True)
        
        return ProductListSerializer(
            products, 
            many=True,
            context=self.context
        ).data