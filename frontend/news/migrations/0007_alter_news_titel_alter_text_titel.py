# Generated by Django 5.2.3 on 2025-06-17 23:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0006_zielgruppe_rename_kategorie_inhaltskategorie_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="news",
            name="titel",
            field=models.CharField(),
        ),
        migrations.AlterField(
            model_name="text",
            name="titel",
            field=models.CharField(),
        ),
    ]
