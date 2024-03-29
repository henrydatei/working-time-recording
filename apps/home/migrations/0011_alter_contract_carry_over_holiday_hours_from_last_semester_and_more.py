# Generated by Django 4.2.1 on 2023-06-27 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0010_alter_contractchange_to_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contract',
            name='carry_over_holiday_hours_from_last_semester',
            field=models.FloatField(default=0, help_text='Usually 0, in the contract overview you can let the number be calculated from the last semester. Only change if you know what you are doing.'),
        ),
        migrations.AlterField(
            model_name='contract',
            name='carry_over_hours_from_last_semester',
            field=models.FloatField(default=0, help_text='Usually 0, in the contract overview you can let the number be calculated from the last semester. Only change if you know what you are doing.'),
        ),
    ]
