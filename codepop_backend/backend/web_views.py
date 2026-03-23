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
    """HTMX endpoint to calculate drink price dynamically - size-based pricing model"""
    if request.method == 'POST':
        # Get cup size
        size = request.POST.get('size', 'm')
        
        # Size-based pricing
        size_prices = {
            's': Decimal('2.00'),  # Small: $2.00
            'm': Decimal('2.50'),  # Medium: $2.50
            'l': Decimal('3.00')   # Large: $3.00
        }
        
        base_price = size_prices.get(size, Decimal('2.50'))

        # Get selected items
        syrups = request.POST.getlist('syrups')
        addins = request.POST.getlist('addins')

        # Calculate additional ingredients cost: $0.30 per ingredient
        ingredient_count = len(syrups) + len(addins)
        ingredient_cost = Decimal('0.30') * ingredient_count

        total_price = base_price + ingredient_cost

        # Size display names
        size_names = {
            's': 'Small',
            'm': 'Medium',
            'l': 'Large'
        }
        size_name = size_names.get(size, 'Medium')

        # Return price display with breakdown
        return HttpResponse(f'''
            <div id="price-display" class="text-6xl font-bold text-white drop-shadow-lg mb-2">
                ${total_price:.2f}
            </div>
            <div class="text-sm opacity-90 mb-2">
                <p>🥤 {size_name} Base Price: <span class="font-bold">${base_price:.2f}</span></p>
                <p id="ingredient-count">✨ Additional Ingredients: <span class="font-bold">{ingredient_count} × $0.30 = ${ingredient_cost:.2f}</span></p>
            </div>
            <p class="text-lg opacity-90 italic">Updates in real-time as you build! 🎨</p>
        ''')

    return HttpResponse('$2.50')


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

        # Calculate price using same logic as calculate_price - size-based pricing model
        size_prices = {
            's': Decimal('2.00'),  # Small: $2.00
            'm': Decimal('2.50'),  # Medium: $2.50
            'l': Decimal('3.00')   # Large: $3.00
        }
        
        base_price = size_prices.get(size, Decimal('2.50'))
        ingredient_count = len(syrups) + len(addins)
        ingredient_cost = Decimal('0.30') * ingredient_count  # $0.30 per ingredient
        total_price = float(base_price + ingredient_cost)

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

        # Size display names for message
        size_names = {
            's': 'Small',
            'm': 'Medium',
            'l': 'Large'
        }
        size_name = size_names.get(size, 'Medium')

        messages.success(request, f'{size_name} "{name}" created successfully! Price: ${total_price:.2f}')
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
