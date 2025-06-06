# Generated by Django 5.1.7 on 2025-05-12 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meteo', '0018_delete_locationpictures'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocationPictures',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('image', models.ImageField(upload_to='photos/')),
                ('latitude', models.CharField(max_length=100)),
                ('longitude', models.CharField(max_length=100)),
            ],
        ),
    ]
