from django.contrib import admin
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

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_code', 'category', 'price', 'stock_quantity', 'is_active']
    list_filter = ['category', 'is_active', 'is_featured', 'gender', 'age_range']
    search_fields = ['name', 'product_code', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'product_code', 'category', 'brand')
        }),
        ('Description', {
            'fields': ('short_description', 'description')
        }),
        ('Baby Specific', {
            'fields': ('gender', 'age_range', 'season', 'material', 'care_instructions')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
        ('Flags', {
            'fields': ('is_active', 'is_featured', 'is_new', 'is_bestseller', 
                      'is_organic', 'is_hypoallergenic')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved']
    search_fields = ['product__name', 'user__email', 'title']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['products']  # Better UI for many-to-many
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product_count', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['products']  # Better UI for many-to-many
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(RecentlyViewed)
class RecentlyViewedAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['viewed_at']
    
    # Optimize queries
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')
