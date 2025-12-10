import os
import django
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'babyshop_backend.settings')
django.setup()

from users.models import CustomUser
from products.models import Category, Brand, Product, ProductImage, ProductVariant, Tag, ProductReview, Wishlist
from django.utils.text import slugify
from decimal import Decimal
import random

def create_superuser():
    """Create admin user if not exists"""
    if not CustomUser.objects.filter(username='admin').exists():
        CustomUser.objects.create_superuser(
            email='admin@babyshop.com',
            username='admin',
            password='admin123'
        )
        print("✓ Admin user created: admin@babyshop.com / admin123")
    else:
        print("✓ Admin user already exists")

def create_test_users():
    """Create regular test users"""
    test_users = []
    for i in range(1, 4):
        username = f'testuser{i}'
        email = f'{username}@example.com'
        
        if not CustomUser.objects.filter(username=username).exists():
            try:
                user = CustomUser.objects.create_user(
                    email=email,
                    username=username,
                    password='password123'
                )
                test_users.append(user)
                print(f"✓ Created test user: {username} ({email})")
            except Exception as e:
                print(f"⚠ Error creating user {username}: {e}")
        else:
            user = CustomUser.objects.get(username=username)
            test_users.append(user)
    
    return test_users

def create_categories():
    """Create categories with proper parent handling"""
    print("\nCreating categories...")
    
    # Check if categories already exist
    existing_categories = Category.objects.all()
    if existing_categories.count() > 0:
        print(f"Found {existing_categories.count()} existing categories")
        return existing_categories
    
    # Create root categories (parent=None)
    root_categories_data = [
        {
            'name': 'Baby Clothing',
            'description': 'Clothing for babies and toddlers',
        },
        {
            'name': 'Baby Gear',
            'description': 'Essentials and equipment for babies',
        },
        {
            'name': 'Toys & Entertainment',
            'description': 'Toys and entertainment for babies',
        },
    ]
    
    root_categories = []
    for cat_data in root_categories_data:
        try:
            # Create with parent=None explicitly
            category = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                parent=None,  # Explicitly set to None
                is_active=True
            )
            root_categories.append(category)
            print(f"✓ Created root category: {cat_data['name']}")
        except Exception as e:
            print(f"⚠ Error creating category {cat_data['name']}: {e}")
            print(f"  Error details: {str(e)}")
    
    # Create subcategories under Baby Clothing
    if root_categories:
        baby_clothing = root_categories[0]
        subcategories_data = [
            {
                'name': 'Onesies & Bodysuits',
                'description': 'One-piece outfits for babies',
                'parent': baby_clothing
            },
            {
                'name': 'Rompers & Sleepsuits',
                'description': 'Rompers and sleepwear',
                'parent': baby_clothing
            },
            {
                'name': 'Baby Tops & T-Shirts',
                'description': 'Shirts and tops for babies',
                'parent': baby_clothing
            },
        ]
        
        for subcat_data in subcategories_data:
            try:
                subcategory = Category.objects.create(
                    name=subcat_data['name'],
                    description=subcat_data['description'],
                    parent=subcat_data['parent'],
                    is_active=True
                )
                print(f"✓ Created subcategory: {subcat_data['name']} under {baby_clothing.name}")
            except Exception as e:
                print(f"⚠ Error creating subcategory {subcat_data['name']}: {e}")
    
    return Category.objects.all()

def create_brands():
    """Create brand data"""
    print("\nCreating brands...")
    
    brands_data = [
        {
            'name': 'Gerber',
            'description': 'Trusted baby care products since 1927',
        },
        {
            'name': 'Carter\'s',
            'description': 'America\'s leading baby and children\'s apparel brand',
        },
        {
            'name': 'Fisher-Price',
            'description': 'Educational toys and baby gear',
        },
        {
            'name': 'Graco',
            'description': 'Innovative solutions for babies and their parents',
        },
    ]
    
    brands = []
    for brand_data in brands_data:
        try:
            brand, created = Brand.objects.get_or_create(
                name=brand_data['name'],
                defaults={
                    'description': brand_data['description'],
                    'is_active': True
                }
            )
            brands.append(brand)
            if created:
                print(f"✓ Created brand: {brand_data['name']}")
        except Exception as e:
            print(f"⚠ Error creating brand {brand_data['name']}: {e}")
    
    return brands

def create_tags():
    """Create product tags"""
    print("\nCreating tags...")
    
    tags_data = [
        'organic', 'eco-friendly', 'bestseller', 'new-arrival',
        'on-sale', 'educational', 'premium', 'hypoallergenic'
    ]
    
    tags = []
    for tag_name in tags_data:
        try:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': slugify(tag_name)}
            )
            tags.append(tag)
            if created:
                print(f"✓ Created tag: {tag_name}")
        except Exception as e:
            print(f"⚠ Error creating tag {tag_name}: {e}")
    
    return tags

def create_products(categories, brands, tags):
    """Create sample products"""
    print("\nCreating products...")
    
    if not categories:
        print("⚠ No categories found. Creating a default category first...")
        # Create a default category
        try:
            default_category = Category.objects.create(
                name='Baby Essentials',
                description='Essential baby products',
                parent=None,
                is_active=True
            )
            categories = [default_category]
            print(f"✓ Created default category: Baby Essentials")
        except Exception as e:
            print(f"⚠ Error creating default category: {e}")
            return []
    
    if not brands:
        print("⚠ No brands found. Creating a default brand first...")
        try:
            default_brand = Brand.objects.create(
                name='BabyShop',
                description='Our own brand',
                is_active=True
            )
            brands = [default_brand]
            print(f"✓ Created default brand: BabyShop")
        except Exception as e:
            print(f"⚠ Error creating default brand: {e}")
            return []
    
    # Get a clothing category
    clothing_category = categories[0]
    
    products_data = [
        {
            'name': 'Organic Cotton Baby Onesie',
            'description': 'Soft 100% organic cotton onesie for newborn babies. Features envelope neckline for easy dressing and snap closures for quick diaper changes.',
            'short_description': 'Soft organic cotton onesie',
            'product_code': 'ONS-001',
            'category': clothing_category,
            'brand': brands[0],
            'gender': 'newborn',
            'age_range': '0-3m',
            'season': 'all_season',
            'material': '100% Organic Cotton',
            'care_instructions': 'Machine wash cold, tumble dry low',
            'price': Decimal('19.99'),
            'compare_at_price': Decimal('24.99'),
            'stock_quantity': 50,
            'is_organic': True,
            'is_hypoallergenic': True,
            'is_featured': True,
            'is_new': True,
            'low_stock_threshold': 10,
        },
        {
            'name': 'Baby Romper with Hat Set',
            'description': 'Adorable 2-piece romper set including matching hat. Made from breathable cotton blend for all-day comfort.',
            'short_description': '2-piece romper set with hat',
            'product_code': 'RMP-002',
            'category': clothing_category,
            'brand': brands[1] if len(brands) > 1 else brands[0],
            'gender': 'unisex',
            'age_range': '3-6m',
            'season': 'summer',
            'material': 'Cotton Blend',
            'care_instructions': 'Machine wash gentle, do not bleach',
            'price': Decimal('29.99'),
            'compare_at_price': Decimal('34.99'),
            'stock_quantity': 30,
            'is_featured': True,
            'is_bestseller': True,
            'low_stock_threshold': 5,
        },
        {
            'name': 'Baby T-Shirt 3-Pack',
            'description': 'Pack of 3 comfortable baby t-shirts in assorted colors. Perfect for everyday wear.',
            'short_description': '3-pack baby t-shirts',
            'product_code': 'TSP-003',
            'category': clothing_category,
            'brand': brands[0],
            'gender': 'boys',
            'age_range': '6-12m',
            'season': 'all_season',
            'material': '100% Cotton',
            'care_instructions': 'Machine wash warm, tumble dry medium',
            'price': Decimal('24.99'),
            'stock_quantity': 75,
            'is_bestseller': True,
            'low_stock_threshold': 15,
        },
    ]
    
    products = []
    for prod_data in products_data:
        try:
            # Check if product already exists
            if Product.objects.filter(product_code=prod_data['product_code']).exists():
                product = Product.objects.get(product_code=prod_data['product_code'])
                print(f"  Product already exists: {prod_data['name']}")
                products.append(product)
                continue
            
            # Create product
            product = Product.objects.create(
                name=prod_data['name'],
                description=prod_data['description'],
                short_description=prod_data['short_description'],
                product_code=prod_data['product_code'],
                category=prod_data['category'],
                brand=prod_data['brand'],
                gender=prod_data['gender'],
                age_range=prod_data['age_range'],
                season=prod_data.get('season', 'all_season'),
                material=prod_data.get('material', ''),
                care_instructions=prod_data.get('care_instructions', ''),
                price=prod_data['price'],
                compare_at_price=prod_data.get('compare_at_price'),
                stock_quantity=prod_data['stock_quantity'],
                low_stock_threshold=prod_data.get('low_stock_threshold', 5),
                is_organic=prod_data.get('is_organic', False),
                is_hypoallergenic=prod_data.get('is_hypoallergenic', False),
                is_featured=prod_data.get('is_featured', False),
                is_new=prod_data.get('is_new', False),
                is_bestseller=prod_data.get('is_bestseller', False),
                is_active=True,
            )
            
            # Add tags
            if prod_data.get('is_organic'):
                organic_tag = Tag.objects.filter(name='organic').first()
                if organic_tag:
                    product.tags.add(organic_tag)
            
            if prod_data.get('is_hypoallergenic'):
                hypo_tag = Tag.objects.filter(name='hypoallergenic').first()
                if hypo_tag:
                    product.tags.add(hypo_tag)
            
            if prod_data.get('is_bestseller'):
                bestseller_tag = Tag.objects.filter(name='bestseller').first()
                if bestseller_tag:
                    product.tags.add(bestseller_tag)
            
            if prod_data.get('is_new'):
                new_tag = Tag.objects.filter(name='new-arrival').first()
                if new_tag:
                    product.tags.add(new_tag)
            
            # Create product images
            ProductImage.objects.create(
                product=product,
                alt_text=f"{product.name} - Main Image",
                is_primary=True,
                order=1
            )
            
            ProductImage.objects.create(
                product=product,
                alt_text=f"{product.name} - Alternate View",
                is_primary=False,
                order=2
            )
            
            # Create variants for clothing products
            sizes = ['newborn', '0-3m', '3-6m']
            colors = ['White', 'Blue', 'Pink']
            color_codes = {
                'White': '#FFFFFF',
                'Blue': '#87CEEB',
                'Pink': '#FFC0CB'
            }
            
            for size in sizes:
                for color in colors:
                    variant_code = f'{product.product_code}-{size[:2]}-{color[:1]}'
                    ProductVariant.objects.create(
                        product=product,
                        size=size,
                        color=color,
                        color_code=color_codes.get(color, '#000000'),
                        product_code=variant_code,
                        stock_quantity=random.randint(5, 15),
                        price_adjustment=Decimal('0.00'),
                        is_active=True
                    )
            
            products.append(product)
            print(f"✓ Created product: {prod_data['name']} (Code: {prod_data['product_code']})")
            
        except Exception as e:
            print(f"⚠ Error creating product {prod_data['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    return products

def create_reviews(products, test_users):
    """Create sample reviews for products"""
    print("\nCreating reviews...")
    
    if not products or not test_users:
        print("⚠ Skipping reviews - no products or users")
        return 0
    
    review_data = [
        {
            'rating': 5,
            'title': 'Perfect fit for my newborn!',
            'comment': 'The onesie fits perfectly and the material is so soft. My baby seems very comfortable in it.',
            'fit_rating': 5,
            'quality_rating': 5,
            'is_verified_purchase': True,
            'helpful_count': 12,
            'is_approved': True,
        },
        {
            'rating': 4,
            'title': 'Good quality, runs slightly small',
            'comment': 'Overall good quality, but I would recommend sizing up. The material is excellent.',
            'fit_rating': 3,
            'quality_rating': 5,
            'is_verified_purchase': True,
            'helpful_count': 5,
            'is_approved': True,
        },
        {
            'rating': 5,
            'title': 'Absolutely love it!',
            'comment': 'My baby looks adorable in this romper. The hat is a nice bonus. Good quality material.',
            'fit_rating': 5,
            'quality_rating': 5,
            'is_verified_purchase': True,
            'helpful_count': 8,
            'is_approved': True,
        },
    ]
    
    review_count = 0
    for product in products:
        for i, review in enumerate(review_data):
            user = test_users[i % len(test_users)] if test_users else None
            if not user:
                continue
            
            try:
                # Check if review already exists
                if not ProductReview.objects.filter(product=product, user=user).exists():
                    ProductReview.objects.create(
                        product=product,
                        user=user,
                        rating=review['rating'],
                        title=review['title'],
                        comment=review['comment'],
                        fit_rating=review['fit_rating'],
                        quality_rating=review['quality_rating'],
                        is_verified_purchase=review['is_verified_purchase'],
                        helpful_count=review['helpful_count'],
                        is_approved=review['is_approved'],
                    )
                    review_count += 1
            except Exception as e:
                print(f"⚠ Error creating review for {product.name}: {e}")
    
    if review_count > 0:
        print(f"✓ Created {review_count} reviews")
    
    return review_count

def create_wishlists(test_users, products):
    """Create sample wishlists"""
    print("\nCreating wishlists...")
    
    if not test_users or not products:
        print("⚠ Skipping wishlists - no users or products")
        return 0
    
    wishlist_count = 0
    for i, user in enumerate(test_users):
        try:
            # Create wishlist for user
            wishlist, created = Wishlist.objects.get_or_create(
                user=user,
                defaults={
                    'name': 'My Wishlist',
                    'is_public': False
                }
            )
            
            if created:
                wishlist_count += 1
                
                # Add some products to wishlist
                if products:
                    # Add first product to first user's wishlist
                    if i == 0:
                        wishlist.products.add(products[0])
                    
                    # Add second product to second user's wishlist
                    if i == 1 and len(products) > 1:
                        wishlist.products.add(products[1])
                    
                    # Add third product to third user's wishlist
                    if i == 2 and len(products) > 2:
                        wishlist.products.add(products[2])
                
                print(f"✓ Created wishlist for {user.username}")
        except Exception as e:
            print(f"⚠ Error creating wishlist for {user.username}: {e}")
    
    return wishlist_count

def main():
    print("Creating comprehensive test data for BabyShop...")
    print("=" * 60)
    
    create_superuser()
    test_users = create_test_users()
    categories = create_categories()
    brands = create_brands()
    tags = create_tags()
    products = create_products(categories, brands, tags)
    review_count = create_reviews(products, test_users)
    wishlist_count = create_wishlists(test_users, products)
    
    print("\n" + "=" * 60)
    print("✅ TEST DATA SUMMARY")
    print("=" * 60)
    print(f"📁 Categories: {Category.objects.count()}")
    print(f"🏷️  Brands: {Brand.objects.count()}")
    print(f"🛍️  Products: {Product.objects.count()}")
    print(f"🖼️  Images: {ProductImage.objects.count()}")
    print(f"🎨 Variants: {ProductVariant.objects.count()}")
    print(f"🏷️  Tags: {Tag.objects.count()}")
    print(f"⭐ Reviews: {ProductReview.objects.count()}")
    print(f"❤️  Wishlists: {Wishlist.objects.count()}")
    print(f"👤 Users: {CustomUser.objects.count()}")
    print(f"\n🔑 Admin Login: admin@babyshop.com / admin123")
    print("🔑 Test Users: testuser1@example.com / password123")
    print("\nYou can now test the API endpoints!")

if __name__ == '__main__':
    main()