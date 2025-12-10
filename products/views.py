from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import generics, status, views, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAdminUser,IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

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

from .serializers import (
    CategorySerializer, CategoryDetailSerializer,
    BrandSerializer, ProductSerializer, ProductDetailSerializer,
    ProductImageSerializer, ProductListSerializer, ProductReviewSerializer,
    ProductVariantSerializer, RecentlyViewedSerializer, TagSerializer,
    WishlistSerializer
)


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    # filtering
    filter_backend = [filters.OrderingFilter]

    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent')

        if parent_id:
            try:
                parent_id = int(parent_id)
                if parent_id == 0:
                    # show only top level categories
                    queryset = queryset.filter(parent__isnull=True)
                else:
                    queryset = queryset.filter(parent_id=parent_id)
            except (ValueError, TypeError):
                pass
        return queryset


class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategoryDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_object(self):
        slug = self.kwargs.get('slug')
        category = get_object_or_404(
            Category.objects.filter(is_active=True)
            .prefetch_related(
                'children',
            ),
            slug=slug
        )
        category._active_products = category.products.filter(is_active=True)

        return category


class CategoryCreateView(generics.CreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]


class CategoryUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'

    def get_queryset(self):
        return Category.objects.all()


class ProductListView(generics.ListAPIView):
    """
    View for listing all products (GET only)
    """
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    # Add filtering, search, and ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Define filter fields (you'll need to create a filterset or specify fields)
    filterset_fields = ['category', 'brand', 'gender', 'age_range', 'is_featured', 'is_bestseller','tags']

    # Search fields
    search_fields = ['name', 'description', 'short_description', 'product_code']

    # Ordering fields
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    ordering = ['-created_at']  # Default: newest first

    def get_queryset(self):
        """Optimize queryset for listing"""
        queryset = Product.objects.filter(is_active=True).select_related(
            'category', 'brand'
        ).prefetch_related(
            'images','tags'
        )

         # Optional: Filter by tag slug (alternative to ID)
        tag_slug = self.request.query_params.get('tag_slug')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        return queryset


class ProductCreateView(generics.CreateAPIView):
    """
    View for creating a new product (POST only)
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Required for CreateAPIView for validation purposes
        """
        return Product.objects.all()

    def perform_create(self, serializer):
        """Handle product creation"""
        # The model's save() method will handle slug generation
        serializer.save()


class ProductDetailView(generics.RetrieveAPIView):
    """
    View for retrieving a single product (GET only)
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        """Optimize queryset for detail view"""
        queryset = Product.objects.filter(is_active=True).select_related(
            'category', 'brand'
        ).prefetch_related(
            'images', 'variants', 'tags', 'reviews'
        )
        return queryset
    
    def retrieve(self,request,*args,**kwargs):
        response = super().retrieve(request,*args,**kwargs)

        #track view if user is authenticated
        if request.user.is_authenticated:
            product = self.get_object()
            RecentlyViewed.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={'viewed_at':timezone.now()}
            )
        return response


class ProductUpdateView(generics.UpdateAPIView):
    """
    View for updating a product (PUT/PATCH only)
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.all()
    

    def update(self, request, *args, **kwargs):
        """Allow partial updates with PATCH method"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)


class ProductDeleteView(generics.DestroyAPIView):
    """
    View for deleting a product (DELETE only)
    """
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.all()

    def perform_destroy(self, instance):
        """Soft delete the product"""
        instance.is_active = False
        instance.save()


# Optional: View for getting inactive products (admin only)
class InactiveProductListView(generics.ListAPIView):
    """
    View for listing inactive products (admin only)
    """
    serializer_class = ProductListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """Get only inactive products"""
        queryset = Product.objects.filter(is_active=False).select_related(
            'category', 'brand'
        ).prefetch_related(
            'images'
        )
        return queryset


# Optional: View for restoring a product
class ProductRestoreView(generics.UpdateAPIView):
    """
    View for restoring a soft-deleted product (admin only)
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=False)

    def perform_update(self, serializer):
        """Restore the product by setting is_active to True"""
        serializer.save(is_active=True)


# Rest of your views for other models...
class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]


class ProductImageListView(generics.ListAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [AllowAny]


class ProductReviewListView(generics.ListCreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Now we can use is_active along with is_approved
        return ProductReview.objects.filter(is_active=True, is_approved=True)
    
    def perform_create(self, serializer):
        """Set the user when creating a review"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            raise serializers.ValidationError("You must be logged in to submit a review.")

# Update other review views to also filter by is_active
class ProductReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only access their own active reviews
        return ProductReview.objects.filter(user=self.request.user, is_active=True)
    
    def update(self, request, *args, **kwargs):
        """Allow partial updates even for PUT requests"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        """Soft delete - set is_active to False"""
        instance.is_active = False
        instance.save()

class ProductReviewsByProductView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=slug)
        return ProductReview.objects.filter(
            product=product, 
            is_active=True,
            is_approved=True
        ).order_by('-created_at')

class UserProductReviewsView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ProductReview.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')

class HelpfulReviewView(generics.UpdateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ProductReview.objects.filter(is_active=True, is_approved=True)


class InactiveProductReviewsView(generics.ListAPIView):
    """
    List all inactive reviews (admin only)
    GET /api/admin/reviews/inactive/
    """
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductReview.objects.filter(is_active=False).order_by('-created_at')

class ReviewRestoreView(generics.UpdateAPIView):
    """
    Restore an inactive review (admin only)
    POST /api/admin/reviews/{id}/restore/
    """
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductReview.objects.filter(is_active=False)
    
    def update(self, request, *args, **kwargs):
        review = self.get_object()
        review.is_active = True
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)

class ProductVariantListView(generics.ListAPIView):
    """
    List all active product variants (public)
    GET /api/v1/variants/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Only show active variants
        return ProductVariant.objects.filter(is_active=True)

# New: Create variant (admin only)
class ProductVariantCreateView(generics.CreateAPIView):
    """
    Create new product variant (admin only)
    POST /api/v1/variants/create/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    
    def perform_create(self, serializer):
        """Set product_code automatically if not provided"""
        variant = serializer.save()
        if not variant.product_code:
            # Auto-generate product code: product-slug-size-color
            variant.product_code = f"{variant.product.slug}-{variant.size}-{variant.color.lower().replace(' ', '-')}"
            variant.save()

# New: Variant detail (public)
class ProductVariantDetailView(generics.RetrieveAPIView):
    """
    Get specific product variant details (public)
    GET /api/v1/variants/{id}/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Public can only see active variants
        return ProductVariant.objects.filter(is_active=True)

# New: Update variant (admin only)
class ProductVariantUpdateView(generics.UpdateAPIView):
    """
    Update product variant (admin only)
    PUT/PATCH /api/v1/variants/{id}/update/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return ProductVariant.objects.all()
    
    def update(self, request, *args, **kwargs):
        """Allow partial updates"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

# New: Delete variant (soft delete, admin only)
class ProductVariantDeleteView(generics.DestroyAPIView):
    """
    Soft delete product variant (admin only)
    DELETE /api/v1/variants/{id}/delete/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(is_active=True)
    
    def perform_destroy(self, instance):
        """Soft delete - set is_active to False"""
        instance.is_active = False
        instance.save()

# New: List inactive variants (admin only)
class InactiveProductVariantView(generics.ListAPIView):
    """
    List all inactive product variants (admin only)
    GET /api/v1/variants/inactive/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(is_active=False)

# New: Restore variant (admin only)
class ProductVariantRestoreView(generics.UpdateAPIView):
    """
    Restore inactive product variant (admin only)
    POST /api/v1/variants/{id}/restore/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(is_active=False)
    
    def update(self, request, *args, **kwargs):
        variant = self.get_object()
        variant.is_active = True
        variant.save()
        serializer = self.get_serializer(variant)
        return Response(serializer.data)

# New: Get variants by product (public)
class ProductVariantByProductView(generics.ListAPIView):
    """
    Get all variants for a specific product (public)
    GET /api/v1/variants/by-product/{product_slug}/
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        return ProductVariant.objects.filter(product=product, is_active=True)

# Optional: Bulk update stock
class BulkStockUpdateView(generics.GenericAPIView):
    """
    Bulk update stock quantities for multiple variants (admin only)
    POST /api/v1/variants/bulk-stock-update/
    Body: [{"id": 1, "stock_quantity": 10}, {"id": 2, "stock_quantity": 5}]
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUser]
    
    def post(self, request, *args, **kwargs):
        updates = request.data  # Expecting list of {id, stock_quantity}
        
        if not isinstance(updates, list):
            return Response(
                {"error": "Expected a list of updates"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_variants = []
        with transaction.atomic():
            for update in updates:
                try:
                    variant_id = update.get('id')
                    stock_quantity = update.get('stock_quantity')
                    
                    if variant_id is None or stock_quantity is None:
                        continue
                    
                    variant = ProductVariant.objects.get(id=variant_id)
                    variant.stock_quantity = stock_quantity
                    variant.save()
                    updated_variants.append(variant)
                    
                except (ProductVariant.DoesNotExist, ValueError):
                    continue
        
        serializer = self.get_serializer(updated_variants, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecentlyViewedListView(generics.ListAPIView):
    serializer_class = RecentlyViewedSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Only show recently viewed items for the authenticated user
        if self.request.user.is_authenticated:
            return RecentlyViewed.objects.filter(user=self.request.user)
        return RecentlyViewed.objects.none()


# Add this view to create recently viewed entries
class AddRecentlyViewedView(generics.CreateAPIView):
    """
    Add product to recently viewed
    POST /api/v1/recently-viewed/add/
    """
    serializer_class = RecentlyViewedSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create recently viewed entry
        recently_viewed, created = RecentlyViewed.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        # If it already exists, update the viewed_at timestamp
        if not created:
            recently_viewed.viewed_at = timezone.now()
            recently_viewed.save()
        
        serializer = self.get_serializer(recently_viewed)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClearRecentlyViewedView(generics.DestroyAPIView):
    """
    Clear all recently viewed items
    DELETE /api/v1/recently-viewed/clear/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        # Delete all recently viewed items for the user
        count, _ = RecentlyViewed.objects.filter(user=request.user).delete()
        return Response(
            {"message": f"Cleared {count} recently viewed items"},
            status=status.HTTP_204_NO_CONTENT
        )
    




class TagListView(generics.ListAPIView):
    """
    List all tags (public)
    GET /api/tags/
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    
    # Add search functionality
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'product_count']
    ordering = ['name']

class TagDetailView(generics.RetrieveAPIView):
    """
    Get tag details including products (public)
    GET /api/tags/{slug}/
    """
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Tag.objects.all()

class TagCreateView(generics.CreateAPIView):
    """
    Create a new tag (admin only)
    POST /api/tags/create/
    """
    serializer_class = TagSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return Tag.objects.all()

class TagUpdateView(generics.UpdateAPIView):
    """
    Update an existing tag (admin only)
    PUT/PATCH /api/tags/{slug}/update/
    """
    serializer_class = TagSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Tag.objects.all()

class TagDeleteView(generics.DestroyAPIView):
    """
    Delete a tag (admin only)
    DELETE /api/tags/{slug}/delete/
    """
    serializer_class = TagSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Tag.objects.all()
    
    def perform_destroy(self, instance):
        # You might want to handle product relationships before deleting
        # Option 1: Just delete (cascade will remove from products)
        instance.delete()
        
        # Option 2: Check if tag is used
        # if instance.products.exists():
        #     raise ValidationError("Cannot delete tag that is assigned to products")
        # instance.delete()

# Optional: View to get products by tag
class TagProductsView(generics.ListAPIView):
    """
    Get all products for a specific tag
    GET /api/tags/{slug}/products/
    """
    serializer_class = ProductListSerializer  # Lightweight product serializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        slug = self.kwargs.get('slug')
        tag = get_object_or_404(Tag, slug=slug)
        return tag.products.filter(is_active=True).select_related(
            'category', 'brand'
        ).prefetch_related('images')


class WishlistListView(generics.ListCreateAPIView):
    """
    Get user's wishlist or create new wishlist
    GET /api/wishlist/ - Get user's wishlist
    POST /api/wishlist/ - Create new wishlist or add products
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # User can only see their own wishlist
        return Wishlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Automatically assign current user
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Custom create to handle two scenarios:
        1. Creating new wishlist
        2. Adding products to existing wishlist
        """
        # Check if user already has a wishlist
        existing_wishlist = Wishlist.objects.filter(user=request.user).first()
        
        if existing_wishlist:
            # User already has wishlist, add products to it
            product_ids = request.data.get('product_ids', [])
            if not product_ids:
                return Response(
                    {"detail": "No products provided to add to wishlist"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add products to existing wishlist
            existing_wishlist.products.add(*product_ids)
            existing_wishlist.save()
            
            serializer = self.get_serializer(existing_wishlist)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Create new wishlist
            return super().create(request, *args, **kwargs)

class WishlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete wishlist
    GET /api/wishlist/{id}/ - Get wishlist details
    PUT/PATCH /api/wishlist/{id}/ - Update wishlist
    DELETE /api/wishlist/{id}/ - Delete wishlist
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # User can only access their own wishlist
        return Wishlist.objects.filter(user=self.request.user)

class WishlistAddProductView(generics.UpdateAPIView):
    """
    Add product(s) to wishlist
    POST /api/wishlist/{id}/add-product/
    Body: {"product_ids": [1, 2, 3]}
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        wishlist = self.get_object()
        product_ids = request.data.get('product_ids', [])
        
        if not product_ids:
            return Response(
                {"detail": "No product IDs provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add products to wishlist
        wishlist.products.add(*product_ids)
        wishlist.save()
        
        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

class WishlistRemoveProductView(generics.UpdateAPIView):
    """
    Remove product(s) from wishlist
    POST /api/wishlist/{id}/remove-product/
    Body: {"product_ids": [1, 2, 3]}
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        wishlist = self.get_object()
        product_ids = request.data.get('product_ids', [])
        
        if not product_ids:
            return Response(
                {"detail": "No product IDs provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove products from wishlist
        wishlist.products.remove(*product_ids)
        wishlist.save()
        
        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

class WishlistClearView(generics.UpdateAPIView):
    """
    Clear all products from wishlist
    POST /api/wishlist/{id}/clear/
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        wishlist = self.get_object()
        
        # Clear all products
        wishlist.products.clear()
        wishlist.save()
        
        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

class CheckProductInWishlistView(generics.GenericAPIView):
    """
    Check if specific products are in user's wishlist
    GET /api/wishlist/check-products/?product_ids=1,2,3
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        product_ids = request.query_params.get('product_ids', '')
        
        if not product_ids:
            return Response(
                {"detail": "No product IDs provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_ids_list = [int(pid.strip()) for pid in product_ids.split(',')]
        except ValueError:
            return Response(
                {"detail": "Invalid product IDs format"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user's wishlist
        wishlist = Wishlist.objects.filter(user=request.user).first()
        
        if not wishlist:
            # User has no wishlist, so no products are in wishlist
            result = {str(pid): False for pid in product_ids_list}
            return Response(result)
        
        # Check which products are in wishlist
        wishlist_product_ids = set(wishlist.products.values_list('id', flat=True))
        result = {
            str(pid): pid in wishlist_product_ids 
            for pid in product_ids_list
        }
        
        return Response(result)

# Optional: Multiple wishlists feature (users can have more than one wishlist)
class UserWishlistsView(generics.ListCreateAPIView):
    """
    User can have multiple wishlists (like "Birthday", "Christmas", etc.)
    GET /api/wishlists/ - List all user's wishlists
    POST /api/wishlists/ - Create new wishlist
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WishlistByNameView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage wishlist by name (if using multiple wishlists)
    GET /api/wishlists/{name}/ - Get wishlist by name
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'name'
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
4.