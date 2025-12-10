from django.urls import path
from .views import( 
    CategoryCreateView,CategoryListView,CategoryDetailView,CategoryUpdateDeleteView,
    ProductListView,ProductCreateView,ProductDetailView,ProductUpdateView,
    ProductDeleteView,InactiveProductListView,ProductRestoreView,
    BrandListView,ProductImageListView,ProductVariantListView,ProductVariantCreateView,
    ProductVariantDeleteView,ProductVariantByProductView,ProductVariantDetailView,
    ProductVariantUpdateView,ProductVariantRestoreView,InactiveProductVariantView,
    BulkStockUpdateView,ProductReviewListView,ProductReviewsByProductView,UserProductReviewsView,
    ProductReviewDetailView,HelpfulReviewView,InactiveProductReviewsView,ReviewRestoreView,
    RecentlyViewedListView,TagListView,TagCreateView,TagDetailView,TagUpdateView,
    TagDeleteView,TagProductsView,WishlistListView,WishlistDetailView,WishlistAddProductView,
    WishlistByNameView,WishlistClearView,WishlistRemoveProductView,CheckProductInWishlistView,
    UserWishlistsView,ClearRecentlyViewedView,AddRecentlyViewedView
    )

urlpatterns = [
    # Category URLs
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/create/', CategoryCreateView.as_view(), name='category-create'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/update/', CategoryUpdateDeleteView.as_view(), name='category-update'),
    path('categories/<slug:slug>/delete/', CategoryUpdateDeleteView.as_view(), name='category-delete'),
    
    # Product URLs
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:slug>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('products/<slug:slug>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    
    # Optional product management URLs (admin only)
    path('products/inactive/', InactiveProductListView.as_view(), name='inactive-product-list'),
    path('products/<slug:slug>/restore/', ProductRestoreView.as_view(), name='product-restore'),

    # Tag urls
    path('tags/', TagListView.as_view(), name='tag-list'),
    path('tags/create/', TagCreateView.as_view(), name='tag-create'),
    path('tags/<slug:slug>/', TagDetailView.as_view(), name='tag-detail'),
    path('tags/<slug:slug>/update/', TagUpdateView.as_view(), name='tag-update'),
    path('tags/<slug:slug>/delete/', TagDeleteView.as_view(), name='tag-delete'),
    path('tags/<slug:slug>/products/', TagProductsView.as_view(), name='tag-products'),

   # Wishlist URLs (Single wishlist per user)
    path('wishlist/', WishlistListView.as_view(), name='wishlist-list'),
    path('wishlist/<int:pk>/', WishlistDetailView.as_view(), name='wishlist-detail'),
    path('wishlist/<int:pk>/add-product/', WishlistAddProductView.as_view(), name='wishlist-add-product'),
    path('wishlist/<int:pk>/remove-product/', WishlistRemoveProductView.as_view(), name='wishlist-remove-product'),
    path('wishlist/<int:pk>/clear/', WishlistClearView.as_view(), name='wishlist-clear'),
    path('wishlist/check-products/', CheckProductInWishlistView.as_view(), name='check-products'),
    
    # Optional: Multiple wishlists
    path('wishlists/', UserWishlistsView.as_view(), name='user-wishlists'),
    path('wishlists/<str:name>/', WishlistByNameView.as_view(), name='wishlist-by-name'),


    # Review URLs
    # Public endpoints
    path('reviews/', ProductReviewListView.as_view(), name='review-list'),
    path('products/<slug:slug>/reviews/', ProductReviewsByProductView.as_view(), name='product-reviews'),
    
    # User-specific endpoints (require authentication)
    path('user/reviews/', UserProductReviewsView.as_view(), name='user-reviews'),
    path('reviews/<int:pk>/', ProductReviewDetailView.as_view(), name='review-detail'),
    path('reviews/<int:pk>/helpful/', HelpfulReviewView.as_view(), name='review-helpful'),#patch
    
    # Admin endpoints
    path('admin/reviews/inactive/', InactiveProductReviewsView.as_view(), name='inactive-reviews'),
    path('admin/reviews/<int:pk>/restore/', ReviewRestoreView.as_view(), name='review-restore'), #put
    

    # Product Variant URLs
    path('variants/', ProductVariantListView.as_view(), name='variant-list'),  # GET (public)
    path('variants/create/', ProductVariantCreateView.as_view(), name='variant-create'),  # POST (admin)
    path('variants/<int:pk>/', ProductVariantDetailView.as_view(), name='variant-detail'),  # GET (public)
    path('variants/<int:pk>/update/', ProductVariantUpdateView.as_view(), name='variant-update'),  # PUT/PATCH (admin)
    path('variants/<int:pk>/delete/', ProductVariantDeleteView.as_view(), name='variant-delete'),  # DELETE (admin)
    path('variants/inactive/', InactiveProductVariantView.as_view(), name='variant-inactive'),  # GET (admin)
    path('variants/<int:pk>/restore/', ProductVariantRestoreView.as_view(), name='variant-restore'),  # POST (admin)
    path('variants/by-product/<slug:product_slug>/', ProductVariantByProductView.as_view(), name='variants-by-product'),  # GET (public)
    path('variants/bulk-stock-update/', BulkStockUpdateView.as_view(), name='bulk-stock-update'),  # NEW - POST (admin)


    # Recently Viewed URLS
    path('recently-viewed/', RecentlyViewedListView.as_view(), name='recently-viewed-list'),
    path('recently-viewed/add/', AddRecentlyViewedView.as_view(), name='add-recently-viewed'),
    path('recently-viewed/clear/', ClearRecentlyViewedView.as_view(), name='clear-recently-viewed'),


    # Other model URLs
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('product-images/', ProductImageListView.as_view(), name='product-image-list'),
    path('variants/', ProductVariantListView.as_view(), name='product-variant-list'),

    path('tags/', TagListView.as_view(), name='tag-list'),
    path('wishlist/', WishlistListView.as_view(), name='wishlist-list'),
]