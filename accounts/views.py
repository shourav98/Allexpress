from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


from carts.views import _cart_id
from carts.models import Cart, CartItem
import requests



from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage  

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email, username=username, password=password)
            user.phone_number = phone_number
            user.save()

            # Send verification email
            current_site = get_current_site(request)
            mail_subject = "Please activate your account"
            message = render_to_string('accounts/activate_verification_mail.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            messages.success(request, 'Registration successful!')
            return redirect('register')

    else:
        form = RegistrationForm()
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)



def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                # Get the session-based cart
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart)

                # If there are session-based cart items, handle merging them with the logged-in user's cart
                if cart_items.exists():
                    product_variation = []
                    for item in cart_items:
                        variations = item.variations.all()
                        product_variation.append(list(variations))

                    # Get the logged-in user's cart items
                    user_cart_items = CartItem.objects.filter(user=user)
                    existing_variations_list = []
                    item_ids = []

                    for item in user_cart_items:
                        existing_variations = item.variations.all()
                        # Sort existing variations to ensure consistent order
                        sorted_existing_variations = sorted(existing_variations, key=lambda v: v.variation_category)
                        existing_variations_list.append(list(sorted_existing_variations))
                        item_ids.append(item.id)

                    # Check for variation matches and update quantities or add new items to the user cart
                    for pr in product_variation:
                        if pr in existing_variations_list:
                            index = existing_variations_list.index(pr)
                            item_id = item_ids[index]
                            items = CartItem.objects.filter(id=item_id)
                            for item in items:
                                item.quantity += 1
                                item.user = user
                                item.save()
                        else:
                            # Reassign the session-based cart items to the logged-in user
                            # cart_item = cart_items.get(variations__in=pr)
                            cart_items = cart_items.filter(variations__in=pr)
                            for cart_item in cart_items:
                                cart_item.quantity += 1
                                cart_item.save()

                            cart_item.user = user
                            cart_item.cart = None  # Remove the association with the session-based cart
                            cart_item.save()

            except Cart.DoesNotExist:
                pass

            # Log the user in
            auth.login(request, user)
            messages.success(request, 'Logged in successfully!')
            url = request.META.get('HTTP_REFERER')
            
            try:
                query = requests.utils.urlparse(url).query
                # print("query: " + query)
                params = dict(x.split('=') for x in query.split('&'))
                # print("params: " + params)
                
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials!')
            return redirect('login')
    return render(request, 'accounts/login.html')






# def login(request):
#     if request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']
#         user = auth.authenticate(email=email, password=password)


#         if user is not None:
#             try:
#                 cart = Cart.objects.get(cart_id = _cart_id(request))
#                 is_cart_item_exists = CartItem.objects.filter(cart = cart).exists()

#                 if is_cart_item_exists:
#                     cart_item = CartItem.objects.filter(cart = cart)
#                     product_variation = []
#                     for item in cart_item:
#                         variation = item.variations.all()
#                         product_variation.append(list(variation))
                    
#                     cart_items = CartItem.objects.filter(product=product, cart=cart)
                    
                    
#                     cart_items = CartItem.objects.filter( user=user)
#                     existing_variations_list = []
#                     item_ids = []

#                     for item in cart_items:
#                         existing_variations = item.variations.all()
#                         # Sort existing variations to ensure consistent order
#                         sorted_existing_variations = sorted(existing_variations, key=lambda v: v.variation_category)
#                         existing_variations_list.append(list(sorted_existing_variations))
#                         item_ids.append(item.id)
                        
                        
#                     for pr in product_variation:
#                         if pr in existing_variations_list:
#                             index = existing_variations_list.index(pr)
#                             item_id = item_ids[index]
#                             item = CartItem.objects.get(id=item_id)
#                             item.quantity += 1
#                             item.user = user
#                             item.save()
#                         else:
#                             cart_item = CartItem.objects.filter(cart = cart)
#                             for item in cart_item:
#                                 item.user = user
#                                 item.save()
                    
#                     # for item in cart_item:
#                     #     item.user = user
#                     #     item.save()
#             except:
#                 pass

#             auth.login(request, user)
#             messages.success(request, 'Logged in successfully!')
#             return redirect('dashboard')
#         else:
#             messages.error(request, 'Invalid credentials!')
#             return redirect('login')
#     return render(request, 'accounts/login.html')



@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')



def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)

    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated!')
        return redirect('login')
    else:
        messages.error(request, 'The activation link is invalid!')
        return redirect('login')


@login_required(login_url = 'login')
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            # Send password reset email
            current_site = get_current_site(request)
            mail_subject = "Reset Your Password"
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            messages.success(request, 'Password reset email has been sent to your email address !')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgotPassword')
    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request, 'The link has been expired!')
        return redirect('login')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']


        if password == confirm_password:
            # uid = request.session.get['uid']
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successfully!')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match!')
            return redirect('resetPassword')
    else:
        return render(request,'accounts/resetPassword.html')
    
