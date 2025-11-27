from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('audience', models.CharField(choices=[('all', 'All Users'), ('custom', 'Selected Users')], default='all', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='NotificationRead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(auto_now_add=True)),
                ('notification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads', to='notifications.notification')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='notification',
            name='recipients',
            field=models.ManyToManyField(blank=True, related_name='notifications', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='notificationread',
            unique_together={('user', 'notification')},
        ),
        migrations.AddIndex(
            model_name='notificationread',
            index=models.Index(fields=['user'], name='notifications_user_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationread',
            index=models.Index(fields=['notification'], name='notifications_notification_idx'),
        ),
    ]
