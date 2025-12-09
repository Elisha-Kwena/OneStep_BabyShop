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



class BrandSeializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id','name','slug','description','logo','is_active']

        read_only_fields = ['slug']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['product','image','id','alt_text','is_primary','oredr']
        read_only_fields = ['product']

class ProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id','product','size','color','color_code','product_code','stock_quantity','price_adjustment','is_active','current_price','in_stock']
        read_only_fields = ['product_code']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True,read_only=True)
    variants = ProductVariantSerializer(many=True,read_only=True)
    category_name = serializers.CharField(source='category.name',read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, allow_null=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['slug', 'created_at', 'updated_at', 'availability_status']



class ProductReviewSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    # Product information
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    
    # Computed fields
    average_rating = serializers.FloatField(read_only=True)
    days_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'product_slug', 'user',
            'rating', 'title', 'comment', 'fit_rating', 'quality_rating',
            'is_verified_purchase', 'helpful_count', 'average_rating',
            'days_ago', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'product_name', 'product_slug', 'average_rating',
            'days_ago', 'is_verified_purchase', 'helpful_count',
            'is_approved', 'created_at', 'updated_at'
        ]
    
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
                if ProductReview.objects.filter(user=user, product=product).exists():
                    raise serializers.ValidationError(
                        "You have already reviewed this product."
                    )
        
        return data


class TagSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'products', 'product_count']
        read_only_fields = ['slug']

class WishlistSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    # Product details
    products_detail = ProductSerializer(source='products', many=True, read_only=True)
    
    # For adding products via API
    product_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        source='products'
    )
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'user', 'products', 'products_detail', 'product_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def validate_product_ids(self, value):
        """Ensure products are active and in stock"""
        for product in value:
            if not product.is_active:
                raise serializers.ValidationError(
                    f"Product '{product.name}' is not active."
                )
            if not product.in_stock:
                raise serializers.ValidationError(
                    f"Product '{product.name}' is out of stock."
                )
        return value



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
        if primary_image:
            return primary_image.image.url
        return None

class ProductDetailSerializer(ProductSerializer):
    """Extended serializer for product detail view"""
    tags = TagSerializer(many=True, read_only=True)
    related_products = serializers.SerializerMethodField()
    review_stats = serializers.SerializerMethodField()
    
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ['tags', 'related_products', 'review_stats']
    
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
    products = ProductListSerializer(many=True,read_only=True)
    
    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['product_count', 'children','products']
