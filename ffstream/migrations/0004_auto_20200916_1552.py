# Generated by Django 2.2.10 on 2020-09-16 19:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ffstream', '0003_stream_saved_as'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='saved_as',
            field=models.CharField(max_length=254, null=True),
        ),
    ]
