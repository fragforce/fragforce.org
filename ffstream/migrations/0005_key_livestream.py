# Generated by Django 3.2.8 on 2021-10-06 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffstream', '0004_auto_20200916_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='key',
            name='livestream',
            field=models.BooleanField(blank=True, default=False, verbose_name='Can be used to live stream via reflector directly'),
        ),
    ]
