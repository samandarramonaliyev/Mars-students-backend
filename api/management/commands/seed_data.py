"""
Management команда для создания начальных данных.
Создаёт администратора, учителя, курсы, примеры заданий и товары магазина.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Course, Task, Product
from datetime import time

User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт начальные данные для приложения Mars Devs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Пароль для администратора (по умолчанию: admin123)'
        )
        parser.add_argument(
            '--teacher-password',
            type=str,
            default='teacher123',
            help='Пароль для учителя (по умолчанию: teacher123)'
        )

    def handle(self, *args, **options):
        admin_password = options['admin_password']
        teacher_password = options['teacher_password']

        self.stdout.write('Создание начальных данных...')

        # Создаём администратора
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@marsdevs.local',
                'first_name': 'Админ',
                'last_name': 'Системы',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Администратор создан: admin / {admin_password}'
            ))
        else:
            self.stdout.write(self.style.WARNING('! Администратор уже существует'))

        # Создаём курсы
        courses_data = [
            {
                'name': 'Frontend разработка',
                'time': time(10, 0),
                'day_of_week': 'MON',
                'description': 'Изучение HTML, CSS, JavaScript и React'
            },
            {
                'name': 'Backend разработка',
                'time': time(14, 0),
                'day_of_week': 'WED',
                'description': 'Изучение Python, Django и баз данных'
            },
            {
                'name': 'Шахматы',
                'time': time(16, 0),
                'day_of_week': 'FRI',
                'description': 'Занятия по шахматам'
            },
        ]

        created_courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                name=course_data['name'],
                defaults=course_data
            )
            created_courses.append(course)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Курс создан: {course.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'! Курс уже существует: {course.name}'))

        # Создаём учителя
        teacher, created = User.objects.get_or_create(
            username='teacher',
            defaults={
                'email': 'teacher@marsdevs.local',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'role': 'TEACHER',
                'phone': '+7 (999) 123-45-67',
            }
        )
        if created:
            teacher.set_password(teacher_password)
            teacher.assigned_courses.set(created_courses[:2])  # Frontend и Backend курсы
            teacher.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Учитель создан: teacher / {teacher_password}'
            ))
        else:
            self.stdout.write(self.style.WARNING('! Учитель уже существует'))

        # Создаём примеры заданий
        tasks_data = [
            {
                'title': 'Создать адаптивную страницу',
                'description': 'Создайте адаптивную веб-страницу с использованием CSS Flexbox или Grid. Страница должна корректно отображаться на мобильных устройствах.',
                'target_group': 'FRONTEND',
                'reward_coins': 50,
            },
            {
                'title': 'Реализовать компонент React',
                'description': 'Создайте React компонент "Карточка товара" с props: название, цена, изображение. Добавьте hover эффект и кнопку "Купить".',
                'target_group': 'FRONTEND',
                'reward_coins': 75,
            },
            {
                'title': 'REST API на Django',
                'description': 'Создайте простой REST API для списка TODO задач: GET (список), POST (создание), DELETE (удаление). Используйте Django REST Framework.',
                'target_group': 'BACKEND',
                'reward_coins': 100,
            },
            {
                'title': 'Работа с базой данных',
                'description': 'Создайте модели Django для блога: Post, Category, Comment. Реализуйте связи между моделями и создайте миграции.',
                'target_group': 'BACKEND',
                'reward_coins': 80,
            },
            {
                'title': 'Общее задание: Git',
                'description': 'Изучите основы Git: создайте репозиторий, сделайте несколько коммитов, создайте ветку и выполните merge.',
                'target_group': 'ALL',
                'reward_coins': 30,
            },
        ]

        for task_data in tasks_data:
            task, created = Task.objects.get_or_create(
                title=task_data['title'],
                defaults=task_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Задание создано: {task.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'! Задание уже существует: {task.title}'))

        # Создаём товары магазина
        products_data = [
            {
                'name': 'Стикерпак "Mars Devs"',
                'description': 'Набор крутых стикеров с логотипом Mars Devs для ноутбука',
                'price': 100,
                'quantity': 50,
            },
            {
                'name': 'Футболка "I code on Mars"',
                'description': 'Чёрная футболка с принтом для настоящих программистов',
                'price': 500,
                'quantity': 20,
            },
            {
                'name': 'Кружка программиста',
                'description': 'Керамическая кружка 350мл с надписью "But it works on my machine"',
                'price': 200,
                'quantity': 30,
            },
            {
                'name': 'Дополнительный час игры',
                'description': 'Сертификат на дополнительный час свободной игры после занятий',
                'price': 150,
                'quantity': 100,
            },
            {
                'name': 'Книга "Python для начинающих"',
                'description': 'Отличная книга для изучения Python с нуля',
                'price': 300,
                'quantity': 10,
            },
        ]

        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Товар создан: {product.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'! Товар уже существует: {product.name}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Начальные данные успешно созданы!'))
        self.stdout.write('')
        self.stdout.write('Учётные записи:')
        self.stdout.write(f'  Админ:   admin / {admin_password}')
        self.stdout.write(f'  Учитель: teacher / {teacher_password}')
        self.stdout.write('')
        self.stdout.write('Админ-панель: http://localhost:8000/admin/')
        self.stdout.write(self.style.SUCCESS('=' * 50))
