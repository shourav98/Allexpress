# Generated by Django 5.1.1 on 2024-10-24 18:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_rename_variation_orderproduct_variations'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderproduct',
            old_name='variations',
            new_name='variation',
        ),
    ]