from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import generics, status, views, permissions,filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny, IsAuthenticated
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
    CategorySerializer,CategoryDetailSerializer,
    BrandSeializer,ProductSerializer,ProductDetailSerializer,
    ProductImageSerializer,ProductListSerializer,ProductReviewSerializer,
    ProductVariantSerializer,RecentlyViewedSerializer,TagSerializer,
    WishlistSerializer
)

class CategoryView(generics.ListAPIView):
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
            except (ValueError,TypeError):
                pass
        return queryset
    
class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategoryDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_object(self):
        slug = self.kwargs.get('slug')
        category =  get_object_or_404(
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
