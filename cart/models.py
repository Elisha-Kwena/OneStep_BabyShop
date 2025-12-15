from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product, ProductVariant
from django.core.validators import MinValueValidator

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for users - No expiration"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        """Total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def unique_items_count(self):
        """Count of unique products/variants in cart"""
        return self.items.count()
    
    @property
    def subtotal(self):
        """Total price of all items before discounts, shipping, tax"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def estimated_total(self):
        """Estimated total (excl. shipping)"""
        return self.subtotal
    
    def add_item(self, product, quantity=1, variant=None, size='', color=''):
        """Add item to cart or update quantity if exists"""
        # Check if item already exists in cart
        existing_item = self.items.filter(
            product=product,
            variant=variant,
            size=size,
            color=color
        ).first()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            return existing_item
        else:
            return CartItem.objects.create(
                cart=self,
                product=product,
                variant=variant,
                quantity=quantity,
                size=size,
                color=color
            )
    
    def update_item_quantity(self, item_id, quantity):
        """Update quantity of specific cart item"""
        try:
            item = self.items.get(id=item_id)
            if quantity <= 0:
                item.delete()
                return None
            item.quantity = quantity
            item.save()
            return item
        except CartItem.DoesNotExist:
            return None
    
    def remove_item(self, item_id):
        """Remove item from cart"""
        try:
            item = self.items.get(id=item_id)
            item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()
        self.save()
    
    def get_item_by_product(self, product, variant=None, size='', color=''):
        """Get cart item for specific product/variant combination"""
        return self.items.filter(
            product=product,
            variant=variant,
            size=size,
            color=color
        ).first()
    
    def has_product(self, product):
        """Check if cart contains a specific product"""
        return self.items.filter(product=product).exists()
    
    # Baby shop specific methods
    def get_age_ranges_in_cart(self):
        """Get all age ranges represented in cart items"""
        age_ranges = set()
        for item in self.items.all():
            if item.product.age_range:
                age_ranges.add(item.product.age_range)
            # Also check variant's product
            if item.variant and item.variant.product.age_range:
                age_ranges.add(item.variant.product.age_range)
        return list(age_ranges)
    
    def get_genders_in_cart(self):
        """Get all genders represented in cart items"""
        genders = set()
        for item in self.items.all():
            if item.product.gender:
                genders.add(item.product.gender)
            if item.variant and item.variant.product.gender:
                genders.add(item.variant.product.gender)
        return list(genders)
    
    def has_gift_items(self):
        """Check if cart contains items suitable for gifting"""
        for item in self.items.all():
            if item.is_gift_suitable:
                return True
        return False
    
    def get_cart_summary(self):
        """Get a summary of cart contents for display"""
        return {
            'total_items': self.total_items,
            'unique_items': self.unique_items_count,
            'subtotal': float(self.subtotal),
            'age_ranges': self.get_age_ranges_in_cart(),
            'genders': self.get_genders_in_cart(),
            'has_gift_items': self.has_gift_items(),
        }


class CartItem(models.Model):
    """Items in the shopping cart"""
    
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'product', 'variant', 'size', 'color']
        indexes = [
            models.Index(fields=['cart', 'product']),
            models.Index(fields=['added_at']),
        ]
    
    def __str__(self):
        variant_info = ""
        if self.variant:
            variant_info = f" ({self.variant.size}/{self.variant.color})"
        elif self.size or self.color:
            variant_info = f" ({self.size}/{self.color})"
        return f"{self.quantity} x {self.product.name}{variant_info}"
    
    @property
    def unit_price(self):
        """Get current unit price"""
        if self.variant:
            return self.variant.current_price
        return self.product.price
    
    @property
    def total_price(self):
        """Calculate total price for this line item"""
        return self.unit_price * self.quantity
    
    @property
    def product_name(self):
        """Get product name with variant info if applicable"""
        if self.variant:
            return f"{self.product.name} - {self.variant.size} {self.variant.color}"
        elif self.size or self.color:
            extra = []
            if self.size:
                extra.append(self.size)
            if self.color:
                extra.append(self.color)
            if extra:
                return f"{self.product.name} - {' '.join(extra)}"
        return self.product.name
    
    @property
    def product_image(self):
        """Get primary product image"""
        primary_image = self.product.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image
        # Fallback to first image
        first_image = self.product.images.first()
        return first_image.image if first_image else None
    
    @property
    def is_available(self):
        """Check if item is currently available"""
        if self.variant:
            return self.variant.stock_quantity >= self.quantity
        return self.product.stock_quantity >= self.quantity
    
    @property
    def availability_status(self):
        """Get availability status"""
        if self.variant:
            stock = self.variant.stock_quantity
        else:
            stock = self.product.stock_quantity
        
        if stock <= 0:
            return 'out_of_stock'
        elif stock < self.quantity:
            return 'low_stock'
        return 'in_stock'
    
    def save(self, *args, **kwargs):
        # Update variant details if available
        if self.variant:
            if not self.size:
                self.size = self.variant.size
            if not self.color:
                self.color = self.variant.color
        
        # Ensure quantity is at least 1
        if self.quantity < 1:
            self.quantity = 1
        
        super().save(*args, **kwargs)
        
        # Update cart's updated_at timestamp
        self.cart.save()
    
    def increase_quantity(self, amount=1):
        """Increase quantity by specified amount"""
        self.quantity += amount
        self.save()
    
    def decrease_quantity(self, amount=1):
        """Decrease quantity by specified amount"""
        self.quantity = max(1, self.quantity - amount)
        self.save()
    
    # Baby shop specific methods
    @property
    def product_gender(self):
        """Get product gender"""
        return self.product.gender
    
    @property
    def product_age_range(self):
        """Get product age range"""
        return self.product.age_range
    
    @property
    def is_gift_suitable(self):
        """Check if this item is suitable for gifting"""
        product = self.product
        return any([
            product.is_new,
            product.is_featured,
            product.is_bestseller,
            product.compare_at_price and product.compare_at_price > product.price
        ])
    
    def get_item_details(self):
        """Get detailed item info for API responses"""
        return {
            'id': self.id,
            'product_id': self.product.id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'size': self.size,
            'color': self.color,
            'variant_id': self.variant.id if self.variant else None,
            'product_image': self.product_image.url if self.product_image else None,
            'is_available': self.is_available,
            'availability_status': self.availability_status,
            'gender': self.product_gender,
            'age_range': self.product_age_range,
            'is_gift_suitable': self.is_gift_suitable,
        }