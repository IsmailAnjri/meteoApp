from django.db import models
from django.contrib.auth.models import User


class Worldcities(models.Model):
    city = models.TextField(blank=True, null=True)
    lat = models.TextField(blank=True, null=True)  # This field type is a guess.
    lng = models.TextField(blank=True, null=True)  # This field type is a guess.
    country = models.TextField(blank=True, null=True)
    id = models.IntegerField(blank=True, primary_key=True)

    class Meta:
        managed = False
        db_table = 'worldcities'

class UserCities(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cities')
    city1 = models.CharField(max_length=100, blank=True, null=True)
    city2 = models.CharField(max_length=100, blank=True, null=True)
    city3 = models.CharField(max_length=100, blank=True, null=True)
    city4 = models.CharField(max_length=100, blank=True, null=True)
    last_location = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s cities"

class UserLastLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='last_locations')
    location_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.location_name}"

