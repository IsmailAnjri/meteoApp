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

class FavouriteCity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} - {self.city}"



