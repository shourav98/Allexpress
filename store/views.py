from carts.views import _cart_id
from django.shortcuts import render, get_object_or_404
from .models import Product
from category.models import Category
from .models import Variation
from carts.models import CartItem
from django.core.paginator import Paginator
from django.db.models import Q


# Create your views here.
def store(request, category_slug=None):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)
    else:
        selected_category = None

    # Filter by price range
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)

    # Filter by size
    sizes = request.GET.getlist('size')  # Multiple selected sizes
    if sizes:
        # Get product IDs that match the selected sizes in the Variation table
        variation_product_ids = Variation.objects.filter(size__in=sizes).values_list('product_id', flat=True)
        products = products.filter(id__in=variation_product_ids)
    # Pagination
    paginator = Paginator(products, 3)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
        'categories': categories,
        'selected_category': selected_category,
        'price_min': price_min,
        'price_max': price_max,
        'selected_size': sizes
    }
    return render(request, 'store/store.html', context)

def product_detail(request, category_slug, product_slug):

    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id = _cart_id(request), product = single_product).exists()

        if category_slug:
            categories = Product.objects.all().filter(category__slug=category_slug)
            product_count = categories.count()
            

    except Exception as e:
        raise e

    context = {
        'single_product': single_product,
        'in_cart' : in_cart,
        'categories': categories,
        
    }



   

    return render(request, 'store/product_detail.html', context)



def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('created_date').filter(Q(discription__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
        
    return render(request,'store/store.html',context)

