# Generated by Django 2.1.2 on 2018-10-05 04:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ffdonations', '0013_auto_20181004_2337'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donationmodel',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
