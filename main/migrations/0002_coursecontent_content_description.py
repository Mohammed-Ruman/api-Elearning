# Generated by Django 5.0.3 on 2024-03-26 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursecontent',
            name='content_description',
            field=models.TextField(default='description'),
        ),
    ]
