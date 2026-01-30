from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_add_quantity_and_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoinNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(verbose_name='Количество coin')),
                ('reason', models.CharField(blank=True, max_length=255, null=True, verbose_name='Причина')),
                ('is_seen', models.BooleanField(default=False, verbose_name='Просмотрено')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coin_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Студент')),
            ],
            options={
                'verbose_name': 'Уведомление о coin',
                'verbose_name_plural': 'Уведомления о coin',
                'ordering': ['-created_at'],
            },
        ),
    ]
