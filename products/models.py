from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User  = get_user_model()



class Category(models.Model):
    """main category for baby clothes"""
    name = models.CharField(max_length=100,unique=True)
    slug = models.SlugField(max_length=150,unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="category_images/",blank=True,null=True)
    parent = models.ForeignKey('self',on_delete=models.CASCADE,blank=True,related_name="children")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    # create a slug for categories if  not provided one
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args,**kwargs)

class Brand(models.Model):
    """Cloothing brands"""
    name = models.CharField(max_length=100,unique=True)
    slug = models.SlugField(max_length=150,unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="brand_logos/",blank=True,null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

class Product(models.Model):
    """Main products or clothes model"""
    GENDER_CHOICES = [
        ('boys','Boys'),
        ('girls','Girls'),
        ('unisex','Unisex'),
        ('newborn','Newborn')
    ]

    AGE_RANGE_CHOICES = [
        ('0-3m', '0-3 Months'),
        ('3-6m', '3-6 Months'),
        ('6-12m', '6-12 Months'),
        ('12-18m', '12-18 Months'),
        ('18-24m', '18-24 Months'),
        ('2-3y', '2-3 Years'),
        ('3-4y', '3-4 Years'),
        ('4-5y', '4-5 Years'),
        ('5-6y', '5-6 Years'),       
    ]

    SEASON_CHOICES = [
        ('summer', 'Summer'),
        ('winter', 'Winter'),
        ('all_season', 'All Season'),
        ('spring', 'Spring'),
        ('autumn', 'Autumn'),
    ]

    AVAILABILITY_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('pre_order', 'Pre-order'),
        ('discontinued', 'Discontinued'),
    ]


    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255,unique=True,blank=True)
    product_code = models.CharField(max_length=100,unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300)

    # relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE,related_name='products')
    brand = models.ForeignKey(Brand,on_delete=models.SET_NULL,null=True,blank=True)

    # Baby specificattributes
    gender = models.CharField(max_length=20,choices=GENDER_CHOICES,default='unisex')
    age_range = models.CharField(max_length=20,choices=AGE_RANGE_CHOICES)
    season = models.CharField(max_length=20,choices=SEASON_CHOICES,default='all_season')


    # product details
    material = models.CharField(max_length=200,blank=True)
    care_instructions = models.TextField(blank=True)
    availability_status = models.CharField(max_length=20,choices=AVAILABILITY_CHOICES,default='in_stock')
    is_organic = models.BooleanField(default=False)
    is_hypoallergenic = models.BooleanField(default=False)

    
    # pricing
    price = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)


    # Inventory
    stock_quantity = models.IntegerField(default=0,validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=5,validators=[MinValueValidator(0)])


    # flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)


    # metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_code','is_active']),
            models.Index(fields=['category','is_active']),
            models.Index(fields=['price','is_active']),
            models.Index(fields=['gender','age_range','season','is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.product_code}"
    

    @property
    def discount_percentage(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0
    
    @property
    def low_stock(self):
        return 0 < self.stock_quantity <= self.low_stock_threshold
    
    def save(self,*args,**kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug

            counter = 1
            
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug


        if self.stock_quantity > self.low_stock_threshold:
            self.availability_status = 'in_stock'
        elif self.stock_quantity > 0:
            self.availability_status = 'low_stock'
        else:
            self.availability_status = 'out_of_stock'

        super().save(*args,**kwargs)
 



class ProductImage(models.Model):
    """Enables multile images per product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=255,blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)


    class Meta:
        ordering = ['order','id']

    def __str__(self):
        return f"image for {self.product.name}"
    
    def save(self,*args,**kwargs):
        if self.is_primary:
            # ensure only one image per product
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args,**kwargs)



class ProductVariant(models.Model):
    """product variants (size, color combinations) """
    SIZE_CHOICES = [
        ('newborn', 'Newborn (NB)'),
        ('0-3m', '0-3 Months'),
        ('3-6m', '3-6 Months'),
        ('6-9m', '6-9 Months'),
        ('9-12m', '9-12 Months'),
        ('12-18m', '12-18 Months'),
        ('18-24m', '18-24 Months'),
        ('2t', '2T (2 Years)'),
        ('3t', '3T (3 Years)'),
        ('4t', '4T (4 Years)'),
        ('5t', '5T (5 Years)'),
        ('6t', '6T (6 Years)'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    color = models.CharField(max_length=50)  # e.g., "Blue", "Pink", "White"
    color_code = models.CharField(max_length=7, blank=True)  # HEX color code
    
    product_code = models.CharField(max_length=100, unique=True)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    price_adjustment = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['product', 'size', 'color']
        ordering = ['product', 'size']

    @property
    def current_price(self):
        return self.product.price + self.price_adjustment
    
    @property
    def in_stock(self):
        return self.stock_quantity > 0
    
class ProductReview(models.Model):
    """Customer reviews and ratings"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    # Additional helpful fields for baby clothes
    fit_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, null=True, blank=True,
        help_text="How did the size fit?"
    )
    quality_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, null=True, blank=True,
        help_text="How was the quality?"
    )
    
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"Review for {self.product.name} by {self.user}"
    
    @property
    def average_rating(self):
        ratings = [self.rating]
        if self.fit_rating:
            ratings.append(self.fit_rating)
        if self.quality_rating:
            ratings.append(self.quality_rating)
        return sum(ratings) / len(ratings)


class Tag(models.Model):
    """Tags for better search and filtering"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    products = models.ManyToManyField(Product, related_name='tags', blank=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    """User wishlist/favorites"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, related_name='wishlisted_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wishlist of {self.user.email}"


class RecentlyViewed(models.Model):
    """Track recently viewed products"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-viewed_at']
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user} viewed {self.product}"
