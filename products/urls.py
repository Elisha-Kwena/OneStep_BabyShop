from django.urls import path
from .views import CategoryView,CategoryDetailView,CategoryCreateView,CategoryUpdateDeleteView,ProductsListView

urlpatterns = [
    # categories
    path("categories/",CategoryView.as_view(),name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('admin/create-categories/', CategoryCreateView.as_view(), name='admin-category-create'),
    path('admin/update-categories/<slug:slug>/', CategoryUpdateDeleteView.as_view(), name='admin-category-update-delete'),

    # products
    path('products/', ProductsListView.as_view(), name='product-list'),
]