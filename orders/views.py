# views.py
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import OrderForm, PaymentMethodForm  # Assuming you have this form for selecting payment method
import datetime
from .models import Order, Payment
from django.conf import settings

from .models import Order, Payment, OrderProduct
from django.contrib import messages

from django.contrib import messages
from carts.models import CartItem
# import sslcommerz  # Ensure to install the SSLCommerz SDK




def payments(request):
    if request.method == 'POST':
        # Get order number and payment method from POST data
        order_number = request.POST.get('order_number')
        payment_method = request.POST.get('payment_method')

        try:
            # Retrieve the order
            order = Order.objects.get(user=request.user, is_ordered=False, order_number=order_number)
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('checkout')

        # Create a Payment object
        payment = Payment(
            user=request.user,
            payment_id=order_number,
            payment_method=payment_method,
            amount_paid=str(order.order_total),
            status='Pending' if payment_method == 'Cash on Delivery' else 'Completed',
        )
        payment.save()

        # Update the order
        order.payment = payment
        order.is_ordered = True
        order.status = 'New'  # Set appropriate status
        order.save()

        # Move cart items to OrderProduct model
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            order_product = OrderProduct()
            order_product.order = order
            order_product.payment = payment
            order_product.user = request.user
            order_product.product = item.product
            order_product.quantity = item.quantity
            order_product.product_price = item.product.price
            order_product.ordered = True
            order_product.save()

            # Add variations if applicable
            order_product.variation.set(item.variations.all())
            order_product.save()

        # Clear the cart
        CartItem.objects.filter(user=request.user).delete()

        # Redirect to order completion page
        return redirect('order_complete', order_number=order.order_number)
    else:
        # Handle GET request, possibly display payment options
        order_number = request.GET.get('order_number')
        payment_method = request.GET.get('payment_method')

        try:
            order = Order.objects.get(user=request.user, is_ordered=False, order_number=order_number)
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('checkout')

        context = {
            'order': order,
            'payment_method': payment_method,
        }
        return render(request, 'orders/payments.html', context)
    


# orders/views.py


@csrf_exempt
def place_order(request):
    current_user = request.user
    
    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0
    total = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
    tax = (2 * total) / 100
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        payment_method = PaymentMethodForm(request.POST)
        if form.is_valid() and payment_method.is_valid():
            # Store all the billing information inside the order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.payment_method = payment_method.cleaned_data['payment_method']
            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # Send confirmation email after saving the order
            send_order_confirmation_email(data)

            # Handle payment method
            if data.payment_method == 'SSLcommerz':
                # Initialize SSLcommerz payment session
                sslcommerz_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
                payload = {
                    'store_id': settings.SSLCOMMERZ_STORE_ID,
                    'store_passwd': settings.SSLCOMMERZ_STORE_PASS,
                    'total_amount': grand_total,
                    'currency': 'BDT',
                    'tran_id': data.order_number,
                    # 'tran_id': order.order_number,
                    'success_url': 'http://127.0.0.1:8000/orders/payment-success/',
                    'fail_url': 'http://127.0.0.1:8000/orders/payment-failed/',
                    'cancel_url': 'http://127.0.0.1:8000/orders/payment-cancel/',
                    'cus_name': data.full_name(),
                    'cus_email': data.email,
                    'cus_phone': data.phone,
                    'cus_add1': data.address_line_1,
                    'cus_city': data.city,
                    'cus_country': data.country,
                    'shipping_method': 'NO',
                    'product_name': 'Products',
                    'product_category': 'General',
                    'product_profile': 'general',
                }

                response = requests.post(sslcommerz_url, data=payload)
                order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
                ssl_response = response.json()

                if ssl_response.get('status') == 'SUCCESS':
                    # Redirect user to SSLcommerz payment page
                    return redirect(ssl_response['GatewayPageURL'])
                else:
                    return redirect('payment_failed')
            elif data.payment_method == 'Cash on Delivery':
                # Handle COD option
                data.is_ordered = True
                data.status = 'Pending'
                data.save()
                CartItem.objects.filter(user=current_user).delete()

                return redirect('order_complete', order_number=data.order_number)
            
            else:
                context = {
                    'order': order,
                    'cart_items': cart_items,
                    'total': total,
                    'tax': tax,
                    'grand_total': grand_total,
                    'payment_method': payment_method,
                }
                return render(request, 'orders/payments.html', context=context)

    return redirect('checkout')

@csrf_exempt
def order_complete(request, order_number):
    print(order_number, request)
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order=order)

        subtotal = 0
        for item in ordered_products:
            subtotal += item.product_price * item.quantity
        transID = request.POST.get('tran_id') or request.GET.get('tran_id') 
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'subtotal': subtotal,
            'transID': transID
        }
        return render(request, 'orders/order_complete.html', context)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('home')

@csrf_exempt
def payment_success(request):
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    val_id = request.POST.get('val_id') or request.GET.get('val_id')
    print(f"Received payment. Transaction ID: {tran_id}, Payment ID: {val_id}")

    try:
        # Find the order using the transaction ID
        order = Order.objects.get(order_number=tran_id, is_ordered=False)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('home')

    # Update payment information and order status
    payment = Payment.objects.create(
        user=order.user,
        payment_id=val_id,
        payment_method='SSLcommerz',
        amount_paid=order.order_total,
        status='Success',
    )
    payment.save()

    # Mark the order as completed
    order.payment = payment
    order.is_ordered = True  # Set the is_ordered flag to True
    order.status = 'Completed'
    order.save()

    # Clear the user's cart after payment
    CartItem.objects.filter(user=order.user).delete()

    # Send confirmation email
    send_order_confirmation_email(order)

    # Render success page with the order context
    # return render(request, 'orders/payment_success.html', {'order': order})
    return render(request, 'orders/order_complete.html', {'order': order})

# Payments view to handle failed payment
def payment_failed(request):
    return render(request, 'orders/payment_failed.html')


def send_order_confirmation_email(order):
    subject = 'Order Confirmation'
    message = (
        f"Dear {order.full_name()},\n\n"
        f"Your order has been successfully placed!\n"
        f"Order Number: {order.order_number}\n"
        f"Total Amount: {order.order_total}\n\n"
        f"Thank you for shopping with us!"
    )
    recipient_email = order.email

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST,  # From email address
        [recipient_email],  # To email address
        fail_silently=False,
    )