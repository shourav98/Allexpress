# Generated by Django 5.1.1 on 2024-10-22 06:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0006_cartitem_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='size',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]