from django import forms
from .models import Worldcities

class AddCityForm(forms.Form):
    city = forms.ModelChoiceField(queryset=Worldcities.objects.all(), label='Select City')
