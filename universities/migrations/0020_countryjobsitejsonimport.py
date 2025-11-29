# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('universities', '0019_applicationdraft_countryjobsite'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryJobSiteJSONImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('json_data', models.TextField(help_text='Paste a JSON array of job sites here. Each object should have: country, site_name, site_url')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Country Job Site JSON Import',
                'verbose_name_plural': 'Country Job Site JSON Imports',
                'ordering': ['-created_at'],
            },
        ),
    ]
