from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Drink, Inventory
from decimal import Decimal


def home(request):
    """Homepage view"""
    return render(request, 'home.html')


def login_view(request):
    """Login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'login.html')


def logout_view(request):
    """Logout view"""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('home')


def drink_builder(request):
    """Drink builder form view"""
    # Get available ingredients from inventory
    sodas = Inventory.objects.filter(ItemType='Soda', Quantity__gt=0).order_by('ItemName')
    syrups = Inventory.objects.filter(ItemType='Syrup', Quantity__gt=0).order_by('ItemName')
    addins = Inventory.objects.filter(ItemType='Add In', Quantity__gt=0).order_by('ItemName')

    context = {
        'sodas': sodas,
        'syrups': syrups,
        'addins': addins,
    }
    return render(request, 'drink_builder.html', context)


def calculate_price(request):
    """HTMX endpoint to calculate drink price dynamically"""
    if request.method == 'POST':
        # Base prices by size
        size_prices = {
            's': Decimal('2.50'),
            'm': Decimal('3.50'),
            'l': Decimal('4.50'),
        }

        size = request.POST.get('size', 'm')
        base_price = size_prices.get(size, size_prices['m'])

        # Get selected items
        syrups = request.POST.getlist('syrups')
        addins = request.POST.getlist('addins')

        # Add syrup costs ($0.50 per syrup)
        syrup_cost = Decimal('0.50') * len(syrups)

        # Add-in costs ($0.75 per add-in)
        addin_cost = Decimal('0.75') * len(addins)

        total_price = base_price + syrup_cost + addin_cost

        # Return just the price for HTMX to swap in
        return HttpResponse(f'${total_price:.2f}')

    return HttpResponse('$0.00')


def create_drink(request):
    """Create a new drink and add to database"""
    if request.method == 'POST':
        name = request.POST.get('name')
        size = request.POST.get('size', 'm')
        ice = request.POST.get('ice', 'normal')
        soda = request.POST.get('soda')
        syrups = request.POST.getlist('syrups')
        addins = request.POST.getlist('addins')

        # Validate required fields
        if not name or not soda:
            messages.error(request, 'Drink name and base soda are required!')
            return redirect('drink_builder')

        # Calculate price (same logic as calculate_price)
        size_prices = {'s': Decimal('2.50'), 'm': Decimal('3.50'), 'l': Decimal('4.50')}
        base_price = size_prices.get(size, size_prices['m'])
        syrup_cost = Decimal('0.50') * len(syrups)
        addin_cost = Decimal('0.75') * len(addins)
        total_price = float(base_price + syrup_cost + addin_cost)

        # Create the drink
        drink = Drink.objects.create(
            Name=name,
            Size=size,
            Ice=ice,
            SodaUsed=[soda],
            SyrupsUsed=syrups if syrups else None,
            AddIns=addins if addins else None,
            Price=total_price,
            User_Created=True,
            Rating=None
        )

        messages.success(request, f'Drink "{name}" created successfully! Price: ${total_price:.2f}')
        return redirect('drink_list')

    return redirect('drink_builder')


def drink_list(request):
    """View all drinks"""
    drinks = Drink.objects.all().order_by('-DrinkID')

    context = {
        'drinks': drinks,
    }
    return render(request, 'drink_list.html', context)


def delete_drink(request, drink_id):
    """Delete a drink (HTMX endpoint)"""
    if request.method == 'DELETE':
        drink = get_object_or_404(Drink, DrinkID=drink_id)
        drink.delete()
        # Return empty response - HTMX will remove the table row
        return HttpResponse('')

    return HttpResponse(status=405)
