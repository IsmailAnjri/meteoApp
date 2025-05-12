import time
from datetime import datetime, date, timedelta
import random
import exifread
from datetime import date
from .models import LocationPictures
from django.shortcuts import render
from django.core.files.storage import default_storage

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
from .models import UserCities
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Create your views here.
@login_required(login_url='/login/')
def home(request):
    fav_record = UserCities.objects.filter(user=request.user).first()
    cities = []
    temps = []
    user_last_location = request.user.last_locations.order_by('-created_at').first()
    last_location = ""
    last_location_temp = ""

    if fav_record:
        if user_last_location:
            last_location = user_last_location.location_name
            city = Worldcities.objects.filter(city__iexact=last_location).first()
            last_location_temp = get_temp([city.lat, city.lng])

        city_names = [fav_record.city1, fav_record.city2, fav_record.city3, fav_record.city4]
        for name in city_names:
            if name:
                city_obj = Worldcities.objects.filter(city__iexact=name).first()
                if city_obj:
                    temp = get_temp([city_obj.lat, city_obj.lng])
                else:
                    temp = None
                cities.append(name)
                temps.append(temp)
            else:
                cities.append(None)
                temps.append(None)
    else:
        cities = [None] * 4
        temps = [None] * 4

    return render(request, 'index.html', {
        'last_location_temp' : last_location_temp,
        'last_location' : last_location,
        'cities': zip(range(1, 5), cities, temps)
    })

@require_GET
@csrf_exempt
@login_required
def search_city(request):
    city_query = request.GET.get('city', '').strip().lower()
    slot = request.GET.get('slot')  # Expected: "1", "2", "3", or "4"

    if not city_query or slot not in ['1', '2', '3', '4']:
        return JsonResponse({'found': False})

    city = Worldcities.objects.filter(city__iexact=city_query).first()
    fav_record = UserCities.objects.filter(user=request.user).first()
    cities = []
    if fav_record:
        city_names = [fav_record.city1, fav_record.city2, fav_record.city3, fav_record.city4]
        for name in city_names:
            if name:
                cities.append(name)
            else:
                cities.append(None)
    else:
        cities = [None] * 4
    print(cities)
    print(city)
    if city:
        if city.city in cities:
            return JsonResponse({'found': True, 'city': city.city, 'exists': True, 'message': 'City already added.'})

        fav_record, _ = UserCities.objects.get_or_create(user=request.user)
        setattr(fav_record, f'city{slot}', city.city)
        fav_record.save()

        temp = get_temp([city.lat, city.lng])
        return JsonResponse({'found': True, 'city': city.city, 'temp': temp})

    return JsonResponse({'found': False})

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
        next_url = request.GET.get('next') or request.POST.get('next')

        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, "Invalid credentials")
            return redirect('/login/')

        login(request, user)

        if next_url:
            if user.is_staff:
                return redirect(next_url)
            else:
                return redirect('/permission-denied/')
        else:
            return redirect('/home')

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

        user = User.objects.filter(username=username)

        if user.exists():
            messages.info(request, "Username already taken!")
            return redirect('/register/')

        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username
        )

        user.set_password(password)
        user.save()

        messages.info(request, 'Account created Successfully! Enter your credentials to login.')
        return redirect('/login/')

    return render(request, 'registration/register.html')

def get_city_name(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    response = requests.get(url, headers={"User-Agent": "weather-app"})
    if response.status_code == 200:
        data = response.json()
        address = data.get("address", {})
        city = address.get("city") or address.get("town") or address.get("village")
        return city
    else:
        return None

def get_weather_data(lat, lon):
    today = date.today()
    start_date = today - timedelta(days=1)
    end_date = today + timedelta(days=1)

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max"
        f"&timezone=auto"
        f"&start_date={start_date}&end_date={end_date}"
    )

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temps = data["daily"]["temperature_2m_max"]
        return {
            "yesterday": temps[0],
            "today": temps[1],
            "tomorrow": temps[2],
        }
    else:
        return None


def random_city_view(request):
    cities = list(Worldcities.objects.all())
    if not cities:
        return render(request, 'random_city.html', {'error': 'No cities in database.'})

    city = random.choice(cities)

    weather = get_weather_data(city.lat, city.lng)
    if not weather:
        return render(request, 'random_city.html', {'error': 'Could not fetch weather data.'})

    return render(request, 'random_city.html', {
        "city": city.city,
        "yesterday": weather["yesterday"],
        "today": weather["today"],
        "tomorrow": weather["tomorrow"],
        "date_today": date.today()
    })

def get_gps_coords_with_id(file):
    tags = exifread.process_file(file)

    def _get_if_exist(data, key):
        return data.get(key)

    def _convert_to_degress(value):
        d, m, s = [float(x.num) / float(x.den) for x in value.values]
        return d + (m / 60.0) + (s / 3600.0)

    lat_ref = _get_if_exist(tags, 'GPS GPSLatitudeRef')
    lat = _get_if_exist(tags, 'GPS GPSLatitude')
    lon_ref = _get_if_exist(tags, 'GPS GPSLongitudeRef')
    lon = _get_if_exist(tags, 'GPS GPSLongitude')

    # Identifier options
    unique_id = _get_if_exist(tags, 'Image UniqueID')
    datetime = _get_if_exist(tags, 'EXIF DateTimeOriginal')
    camera_model = _get_if_exist(tags, 'Image Model')

    identifier = unique_id or datetime or camera_model or "No ID available"

    if lat and lon and lat_ref and lon_ref:
        lat = _convert_to_degress(lat)
        if lat_ref.values != 'N':
            lat = -lat

        lon = _convert_to_degress(lon)
        if lon_ref.values != 'E':
            lon = -lon

        return {
            "latitude": lat,
            "longitude": lon,
            "identifier": str(identifier)
        }
    else:
        return None

def upload_city_view(request):
    if request.method == 'POST' and request.FILES.get('photo'):
        image = request.FILES['photo']
        title = request.POST.get('title', image.name)

        allowed_types = ['image/jpeg', 'image/png']
        if image.content_type not in allowed_types:
            return render(request, 'upload_city.html', {'error': 'Invalid file type. Only JPG and PNG allowed.'})

        temp_path = default_storage.save(f'temp/{image.name}', image)
        with default_storage.open(temp_path, 'rb') as f:
            gps_info = get_gps_coords_with_id(f)

        if not gps_info:
            return render(request, 'upload_city.html', {'error': 'Image has no GPS data.'})

        identifier = gps_info['identifier']
        lat = str(gps_info['latitude'])
        lon = str(gps_info['longitude'])

        if not LocationPictures.objects.filter(title=identifier).exists():
            picture = LocationPictures.objects.create(
                title=identifier,
                image=image,
                latitude=lat,
                longitude=lon
            )
        else:
            picture = LocationPictures.objects.get(title=identifier)

        weather = get_weather_data(picture.latitude, picture.longitude)
        if not weather:
            return render(request, 'upload_city.html', {'error': 'Could not fetch weather data.'})

        location_name = get_city_name(picture.latitude, picture.longitude)
        return render(request, 'upload_city.html', {
            'city': location_name,
            'yesterday': weather["yesterday"],
            'today': weather["today"],
            'tomorrow': weather["tomorrow"],
            'date_today': date.today(),
            'photo': picture
        })

    return render(request, 'upload_city.html')


def my_meteo(request):
    location = geocoder.ip('me').latlng
    my_temp = get_weather_data(location[0], location[1])
    template = loader.get_template('my_meteo.html')

    location_name = get_city_name(location[0], location[1])
    UserLastLocation.objects.create(user=request.user, location_name=location_name)
    #print("location name: " + location_name)
    context = {
        "location_name": location_name,
        "temp": my_temp,
        "yesterday": my_temp["yesterday"],
        "today": my_temp["today"],
        "tomorrow": my_temp["tomorrow"],
        "date_today": date.today()
    }
    return HttpResponse(template.render(context, request))

def get_temp(location, max_retries=5, retry_delay=1):
    endpoint = "http://api.open-meteo.com/v1/forecast"
    api_request = f"{endpoint}?latitude={location[0]}&longitude={location[1]}&hourly=temperature_2m"

    # Retry logic setup
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.1)  # Reduced backoff factor for quicker retries
    session.mount('http://', HTTPAdapter(max_retries=retries))

    attempt = 0
    while attempt < max_retries:
        try:
            # Send request with a 5-second timeout
            response = session.get(api_request, timeout=5)
            response.raise_for_status()  # Will raise an error for 4xx/5xx responses
            meteo_data = response.json()

            # Get the current hour's temperature
            now = datetime.now()
            hour = now.hour
            temp = round(meteo_data['hourly']['temperature_2m'][hour])

            return temp

        except requests.exceptions.RequestException as e:
            attempt += 1
            print(f"[WARN] Attempt {attempt} failed: {e}")
            if attempt >= max_retries:
                print("[ERROR] Max retries reached. Could not fetch temperature.")
                return None  # Fallback when max retries reached

            # Wait a shorter time before retrying
            print(f"[INFO] Retrying in {retry_delay} second(s)...")
            time.sleep(retry_delay)  # Wait before retrying


@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_staff, login_url='/permission-denied/')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user != request.user:
        UserCities.objects.filter(user=user).delete()
        user.delete()
        messages.success(request, 'User deleted successfully.')
    else:
        messages.warning(request, "You cannot delete yourself.")
    return redirect('admin_dash')
