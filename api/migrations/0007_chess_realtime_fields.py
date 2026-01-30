from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_coinnotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='chessgame',
            name='move_history',
            field=models.JSONField(blank=True, default=list, verbose_name='История ходов'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='white_time',
            field=models.IntegerField(default=300, verbose_name='Время белых (сек)'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='black_time',
            field=models.IntegerField(default=300, verbose_name='Время чёрных (сек)'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='last_move_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время последнего хода'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='ended_reason',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Причина завершения'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='winner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_chess_games', to=settings.AUTH_USER_MODEL, verbose_name='Победитель'),
        ),
        migrations.AddField(
            model_name='chessgame',
            name='loser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lost_chess_games', to=settings.AUTH_USER_MODEL, verbose_name='Проигравший'),
        ),
    ]
