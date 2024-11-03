from django.shortcuts import render
from store.models import Product
def home(request):
    products = Product.objects.all().filter(is_available=True)
    context = {
        'products': products,
    }

    return render(request, 'home.html', context)


def search(request):
    query = request.GET.get('keyword', '')
    results = Product.objects.filter(product_name__icontains=query)  # Adjust the field based on your model
    return render(request, 'home.html', {'products': results, 'query': query})
