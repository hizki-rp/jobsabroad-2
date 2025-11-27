# Generated migration for enhanced scraper fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('universities', '0011_universityjsonimport_remove_university_degree_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='university',
            name='tuition_fee_domestic',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='university',
            name='tuition_fee_international',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='university',
            name='deposit_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='university',
            name='deposit_deadlines',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='university',
            name='housing_info',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='university',
            name='visa_requirements',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='university',
            name='intakes',
            field=models.JSONField(blank=True, default=list, help_text='List of intake periods with application and deposit deadlines.'),
        ),
        migrations.AlterModelOptions(
            name='university',
            options={'ordering': ['name'], 'verbose_name': 'University', 'verbose_name_plural': 'Universities'},
        ),
    ]