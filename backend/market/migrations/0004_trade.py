# Generated manually for Trade model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('market', '0003_spreadbid'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(choices=[('LONG', 'Long'), ('SHORT', 'Short')], help_text='Whether user is going long or short', max_length=5)),
                ('price', models.FloatField(help_text='Price at which the trade was executed')),
                ('quantity', models.IntegerField(default=1, help_text='Number of units traded')),
                ('trade_time', models.DateTimeField(auto_now_add=True, help_text='When this trade was placed')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this trade was last updated')),
                ('market', models.ForeignKey(help_text='The market this trade is for', on_delete=django.db.models.deletion.CASCADE, related_name='trades', to='market.market')),
                ('user', models.ForeignKey(help_text='User placing the trade', on_delete=django.db.models.deletion.CASCADE, related_name='trades', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Trade',
                'verbose_name_plural': 'Trades',
                'ordering': ['-trade_time'],
            },
        ),
        migrations.AddIndex(
            model_name='trade',
            index=models.Index(fields=['market', 'position'], name='market_trade_market__b8e8e8_idx'),
        ),
        migrations.AddIndex(
            model_name='trade',
            index=models.Index(fields=['user', 'trade_time'], name='market_trade_user_id_b8e8e8_idx'),
        ),
        migrations.AddIndex(
            model_name='trade',
            index=models.Index(fields=['market', 'trade_time'], name='market_trade_market__b8e8e9_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='trade',
            unique_together={('market', 'user')},
        ),
    ] 