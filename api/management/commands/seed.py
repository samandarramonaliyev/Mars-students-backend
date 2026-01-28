"""
Alias для команды seed_data.
Использование: python manage.py seed
"""
from .seed_data import Command as SeedDataCommand


class Command(SeedDataCommand):
    """Alias для seed_data команды."""
    help = 'Создаёт начальные данные (alias для seed_data)'
