from datetime import datetime

import geocoder
import requests
from django.http import HttpResponse, JsonResponse
from django.template import loader
from meteo.models import Worldcities
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .models import *
from collections import defaultdict
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import FavouriteCity


# Create your views here.
@login_required(login_url='/login/')
def home(request):
    fav_record = FavouriteCity.objects.filter(user=request.user).first()
    fav_city = fav_record.city if fav_record else None

    temp = None
    if fav_record:
        city_obj = Worldcities.objects.filter(city__iexact=fav_record.city).first()
        if city_obj:
            temp = get_temp([city_obj.lat, city_obj.lng])

    return render(request, 'index.html', {
        'fav_city': fav_city,
        'fav_city_temp': temp
    })


def staff_only(user):
    return user.is_authenticated and user.is_staff

@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_staff, login_url='/permission-denied/')
def admin_page(request):
    users = User.objects.all()
    return render(request, 'admin_dash.html', {'users': users})
def permission_denied(request):
    return render(request, 'permission_denied.html')

def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.GET.get('next') or request.POST.get('next')  # Handle both GET and POST

        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, "Invalid credentials")
            return redirect('/login/')  # You might want to keep 'next' here too

        login(request, user)

        # Handle redirection after login
        if next_url:
            if user.is_staff:
                return redirect(next_url)
            else:
                return redirect('/permission-denied/')
        else:
            return redirect('/home')  # Default landing

    # GET request
    next_url = request.GET.get('next', '')
    return render(request, 'registration/login.html', {'next': next_url})



def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if a user with the provided username already exists
        user = User.objects.filter(username=username)

        if user.exists():
            # Display an information message if the username is taken
            messages.info(request, "Username already taken!")
            return redirect('/register/')

        # Create a new User object with the provided information
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username
        )

        # Set the user's password and save the user object
        user.set_password(password)
        user.save()

        # Display an information message indicating successful account creation
        messages.info(request, 'Account created Successfully! Please <a href="/login/">click here</a> to login.')
        return redirect('/register/')

    # Render the registration page template (GET request)
    return render(request, 'registration/register.html')



def temp_somewhere(request):
    random_city = Worldcities.objects.order_by('?').first()
    city_name = random_city.city
    temp = get_temp([random_city.lat, random_city.lng])

    random_cities = list(Worldcities.objects.exclude(city=city_name).order_by('?')[:20])

    similar_cities = [city.city for city in random_cities if get_temp([city.lat, city.lng]) == temp][:5]
    if not similar_cities:
        return temp_somewhere(request)

    temp_city_map = defaultdict(list)
    for city in random_cities:
        city_temp = get_temp([city.lat, city.lng])
        temp_city_map[city_temp].append(city.city)

    temp_chart_data = list(temp_city_map.items())[:5]

    return render(request, "meteo.html", {
        "city": city_name,
        "temp": temp,
        "similar_cities": similar_cities,
        "temp_chart_data": temp_chart_data
    })

def temp_here(request):
    location = geocoder.ip('me').latlng
    temp = get_temp(location)

    random_cities = list(Worldcities.objects.exclude(city='Your location').order_by('?')[:20])

    similar_cities = [city.city for city in random_cities if get_temp([city.lat, city.lng]) == temp][:5]
    if not similar_cities:
        return temp_somewhere(request)

    temp_city_map = defaultdict(list)
    for city in random_cities:
        city_temp = get_temp([city.lat, city.lng])
        temp_city_map[city_temp].append(city.city)

    temp_chart_data = list(temp_city_map.items())[:5]

    template = loader.get_template('meteo.html')
    context = {
        'city': 'Your location',
        'temp': temp,
        'similar_cities': similar_cities,
        'temp_chart_data': temp_chart_data
    }

    return HttpResponse(template.render(context, request))



def get_temp(location):
    """Fetch the current temperature from Open-Meteo API and return the rounded integer."""
    endpoint = "http://api.open-meteo.com/v1/forecast"
    api_request = f"{endpoint}?latitude={location[0]}&longitude={location[1]}&hourly=temperature_2m"
    now = datetime.now()
    hour = now.hour
    meteo_data = requests.get(api_request).json()
    temp = round(meteo_data['hourly']['temperature_2m'][hour])  # Round temperature to nearest integer
    return temp


def temp_chart(request, temp):
    sampled_cities = Worldcities.objects.order_by('?')[:20]  # Get 50 random cities
    matching_cities = [city.city for city in sampled_cities if get_temp([city.lat, city.lng]) == temp]

    # Limit to 5 cities
    matching_cities = matching_cities[:5]

    chart_data = {
        "labels": [f"{temp}°C"] * len(matching_cities),
        "data": [len(matching_cities)]
    }

    return JsonResponse(chart_data)

@require_GET
@csrf_exempt
@login_required
def search_city(request):
    city_query = request.GET.get('city', '').strip().lower()
    if not city_query:
        return JsonResponse({'found': False})

    city = Worldcities.objects.filter(city__iexact=city_query).first()

    if city:
        FavouriteCity.objects.update_or_create(
            user=request.user,
            defaults={'city': city.city}
        )
        temp = get_temp([city.lat, city.lng])

        return JsonResponse({'found': True, 'city': city.city, 'temp': temp})

    return JsonResponse({'found': False})

@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_staff, login_url='/permission-denied/')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user != request.user:
        FavouriteCity.objects.filter(user=user).delete()
        user.delete()
        messages.success(request, 'User deleted successfully.')
    else:
        messages.warning(request, "You cannot delete yourself.")
    return redirect('admin_dash')
