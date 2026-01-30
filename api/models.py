"""
Модели базы данных для приложения Mars Devs.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.conf import settings
import os
import uuid


def avatar_upload_path(instance, filename):
    """Генерация пути для загрузки аватара."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('avatars', filename)


def submission_upload_path(instance, filename):
    """Генерация пути для загрузки файлов заданий."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('submissions', filename)


class User(AbstractUser):
    """
    Расширенная модель пользователя.
    Роли: ADMIN, TEACHER, STUDENT
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        TEACHER = 'TEACHER', 'Преподаватель'
        STUDENT = 'STUDENT', 'Студент'
    
    class StudentGroup(models.TextChoices):
        FRONTEND = 'FRONTEND', 'Frontend'
        BACKEND = 'BACKEND', 'Backend'
        NONE = 'NONE', 'Не указано'
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        verbose_name='Аватар'
    )
    nickname = models.CharField(max_length=50, blank=True, verbose_name='Никнейм')
    
    # Поля специфичные для студентов
    student_group = models.CharField(
        max_length=10,
        choices=StudentGroup.choices,
        default=StudentGroup.NONE,
        verbose_name='Группа студента'
    )
    parent_info = models.TextField(blank=True, verbose_name='Информация о родителях')
    balance = models.IntegerField(default=0, verbose_name='Баланс монет')
    
    # Связь с курсами (для учителей)
    assigned_courses = models.ManyToManyField(
        'Course',
        blank=True,
        related_name='teachers',
        verbose_name='Назначенные курсы'
    )
    
    # Учитель, создавший студента
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_students',
        verbose_name='Создан учителем'
    )
    
    # Оригинальный пароль (только для просмотра учителем)
    raw_password = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Пароль (для учителя)'
    )
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER
    
    @property
    def is_student(self):
        return self.role == self.Role.STUDENT


class Course(models.Model):
    """Модель курса."""
    class DayOfWeek(models.TextChoices):
        MONDAY = 'MON', 'Понедельник'
        TUESDAY = 'TUE', 'Вторник'
        WEDNESDAY = 'WED', 'Среда'
        THURSDAY = 'THU', 'Четверг'
        FRIDAY = 'FRI', 'Пятница'
        SATURDAY = 'SAT', 'Суббота'
        SUNDAY = 'SUN', 'Воскресенье'
    
    name = models.CharField(max_length=100, verbose_name='Название курса')
    time = models.TimeField(verbose_name='Время занятия')
    day_of_week = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
        verbose_name='День недели'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
    
    def __str__(self):
        return f"{self.name} ({self.get_day_of_week_display()} {self.time})"


class Task(models.Model):
    """Модель задания."""
    class TargetGroup(models.TextChoices):
        FRONTEND = 'FRONTEND', 'Frontend'
        BACKEND = 'BACKEND', 'Backend'
        ALL = 'ALL', 'Все группы'
    
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    target_group = models.CharField(
        max_length=10,
        choices=TargetGroup.choices,
        verbose_name='Целевая группа'
    )
    reward_coins = models.PositiveIntegerField(default=0, verbose_name='Награда в монетах')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Дедлайн')
    
    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_target_group_display()})"


class TaskSubmission(models.Model):
    """Модель отправки выполненного задания."""
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'На проверке'
        APPROVED = 'APPROVED', 'Одобрено'
        REJECTED = 'REJECTED', 'Отклонено'
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Задание'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_submissions',
        verbose_name='Студент'
    )
    text_answer = models.TextField(blank=True, verbose_name='Текстовый ответ')
    file_answer = models.FileField(
        upload_to=submission_upload_path,
        blank=True,
        null=True,
        verbose_name='Файл ответа'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    grade = models.PositiveIntegerField(null=True, blank=True, verbose_name='Оценка')
    teacher_comment = models.TextField(blank=True, verbose_name='Комментарий учителя')
    coins_awarded = models.IntegerField(default=0, verbose_name='Начислено монет')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата проверки')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions',
        verbose_name='Проверил'
    )
    
    class Meta:
        verbose_name = 'Отправка задания'
        verbose_name_plural = 'Отправки заданий'
        ordering = ['-submitted_at']
        # Студент может отправить задание только один раз
        unique_together = ['task', 'student']
    
    def __str__(self):
        return f"{self.student.username} - {self.task.title}"


class CoinTransaction(models.Model):
    """Модель транзакции монет."""
    class Source(models.TextChoices):
        TASK = 'TASK', 'За задание'
        TEACHER = 'TEACHER', 'От учителя'
        ADMIN = 'ADMIN', 'От админа'
        CHESS = 'CHESS', 'За шахматы'
        OTHER = 'OTHER', 'Другое'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coin_transactions',
        verbose_name='Пользователь'
    )
    amount = models.IntegerField(verbose_name='Сумма')  # Может быть отрицательным
    reason = models.CharField(max_length=200, verbose_name='Причина')
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.OTHER,
        verbose_name='Источник'
    )
    balance_after = models.IntegerField(verbose_name='Баланс после операции')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_transactions',
        verbose_name='Создал'
    )
    
    class Meta:
        verbose_name = 'Транзакция монет'
        verbose_name_plural = 'Транзакции монет'
        ordering = ['-created_at']
    
    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.username}: {sign}{self.amount} ({self.reason})"


class TypingResult(models.Model):
    """Модель результата теста печати."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='typing_results',
        verbose_name='Пользователь'
    )
    wpm = models.PositiveIntegerField(verbose_name='Слов в минуту')
    accuracy = models.FloatField(verbose_name='Точность (%)')
    characters_typed = models.PositiveIntegerField(verbose_name='Символов напечатано')
    errors = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
    duration_seconds = models.PositiveIntegerField(verbose_name='Длительность (сек)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    
    class Meta:
        verbose_name = 'Результат печати'
        verbose_name_plural = 'Результаты печати'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.wpm} WPM ({self.accuracy}%)"


class ChessGameHistory(models.Model):
    """Модель истории шахматных игр (записывается учителем вручную)."""
    class Result(models.TextChoices):
        WIN = 'WIN', 'Победа'
        LOSS = 'LOSS', 'Поражение'
        DRAW = 'DRAW', 'Ничья'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chess_games',
        verbose_name='Игрок'
    )
    opponent_name = models.CharField(max_length=100, verbose_name='Имя соперника')
    result = models.CharField(
        max_length=4,
        choices=Result.choices,
        verbose_name='Результат'
    )
    notes = models.TextField(blank=True, verbose_name='Заметки')
    played_at = models.DateTimeField(verbose_name='Дата игры')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_chess_games',
        verbose_name='Записал'
    )
    
    class Meta:
        verbose_name = 'Шахматная игра (ручная)'
        verbose_name_plural = 'Шахматные игры (ручные)'
        ordering = ['-played_at']
    
    def __str__(self):
        return f"{self.user.username} vs {self.opponent_name}: {self.get_result_display()}"


class ChessGame(models.Model):
    """Модель шахматной партии (реальная игра на платформе)."""
    class OpponentType(models.TextChoices):
        BOT = 'BOT', 'Бот'
        STUDENT = 'STUDENT', 'Студент'
    
    class BotLevel(models.TextChoices):
        EASY = 'easy', 'Легкий'
        MEDIUM = 'medium', 'Средний'
        HARD = 'hard', 'Сложный'
    
    class Result(models.TextChoices):
        WIN = 'WIN', 'Победа'
        LOSE = 'LOSE', 'Поражение'
        DRAW = 'DRAW', 'Ничья'
    
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', 'В процессе'
        FINISHED = 'FINISHED', 'Завершена'
        ABANDONED = 'ABANDONED', 'Прервана'
    
    # Игрок
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='played_chess_games',
        verbose_name='Игрок'
    )
    
    # Тип противника
    opponent_type = models.CharField(
        max_length=10,
        choices=OpponentType.choices,
        verbose_name='Тип противника'
    )
    
    # Уровень бота (если играем с ботом)
    bot_level = models.CharField(
        max_length=10,
        choices=BotLevel.choices,
        null=True,
        blank=True,
        verbose_name='Уровень бота'
    )
    
    # Противник-студент (если PvP)
    opponent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opponent_chess_games',
        verbose_name='Противник'
    )
    
    # Статус игры
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name='Статус'
    )
    
    # Результат (для игрока player)
    result = models.CharField(
        max_length=4,
        choices=Result.choices,
        null=True,
        blank=True,
        verbose_name='Результат'
    )
    
    # Начисленные монеты
    coins_earned = models.IntegerField(default=0, verbose_name='Заработано монет')
    
    # Позиция (FEN) для PvP
    fen_position = models.CharField(
        max_length=100,
        default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        verbose_name='Позиция (FEN)'
    )

    # История ходов (SAN)
    move_history = models.JSONField(
        default=list,
        blank=True,
        verbose_name='История ходов'
    )
    
    # Последний ход
    last_move = models.CharField(max_length=10, blank=True, verbose_name='Последний ход')
    
    # Чей ход (для PvP): 'white' или 'black'
    current_turn = models.CharField(max_length=5, default='white', verbose_name='Чей ход')

    # Таймеры (в секундах)
    white_time = models.IntegerField(default=300, verbose_name='Время белых (сек)')
    black_time = models.IntegerField(default=300, verbose_name='Время чёрных (сек)')

    # Время последнего хода
    last_move_at = models.DateTimeField(null=True, blank=True, verbose_name='Время последнего хода')
    
    # Кто играет белыми (для PvP)
    white_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='white_chess_games',
        verbose_name='Белые'
    )
    
    # Время
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начало')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Окончание')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    # Причина завершения
    ended_reason = models.CharField(max_length=20, null=True, blank=True, verbose_name='Причина завершения')

    # Победитель и проигравший
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_chess_games',
        verbose_name='Победитель'
    )
    loser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lost_chess_games',
        verbose_name='Проигравший'
    )
    
    class Meta:
        verbose_name = 'Шахматная партия'
        verbose_name_plural = 'Шахматные партии'
        ordering = ['-started_at']
    
    def __str__(self):
        opponent_name = self.opponent.username if self.opponent else f'Бот ({self.bot_level})'
        return f"{self.player.username} vs {opponent_name}"
    
    def get_opponent_display(self):
        """Возвращает отображаемое имя противника."""
        if self.opponent_type == self.OpponentType.BOT:
            levels = {'easy': 'Легкий', 'medium': 'Средний', 'hard': 'Сложный'}
            return f"Бот ({levels.get(self.bot_level, self.bot_level)})"
        return self.opponent.username if self.opponent else 'Неизвестный'


class ChessInvite(models.Model):
    """Модель приглашения в шахматную партию."""
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Ожидает'
        ACCEPTED = 'ACCEPTED', 'Принято'
        DECLINED = 'DECLINED', 'Отклонено'
        EXPIRED = 'EXPIRED', 'Истекло'
    
    # Кто приглашает
    from_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chess_invites',
        verbose_name='Отправитель'
    )
    
    # Кого приглашают
    to_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_chess_invites',
        verbose_name='Получатель'
    )
    
    # Статус приглашения
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    
    # Созданная игра (после принятия)
    game = models.OneToOneField(
        ChessGame,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invite',
        verbose_name='Игра'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Приглашение в шахматы'
        verbose_name_plural = 'Приглашения в шахматы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_player.username} → {self.to_player.username} ({self.get_status_display()})"


class CoinNotification(models.Model):
    """Уведомление о начислении coin студенту."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coin_notifications',
        verbose_name='Студент'
    )
    amount = models.IntegerField(verbose_name='Количество coin')
    reason = models.CharField(max_length=255, null=True, blank=True, verbose_name='Причина')
    is_seen = models.BooleanField(default=False, verbose_name='Просмотрено')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Уведомление о coin'
        verbose_name_plural = 'Уведомления о coin'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} +{self.amount} coin"


def product_image_upload_path(instance, filename):
    """Генерация пути для загрузки изображений товаров."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('products', filename)


class Product(models.Model):
    """
    Модель товара в магазине.
    Товар — ОБЩИЙ, добавляется через admin, виден всем студентам.
    НЕ содержит код — код генерируется при покупке.
    """
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name='Изображение'
    )
    price = models.PositiveIntegerField(verbose_name='Цена (монеты)')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество на складе')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.price} монет)"
    
    @property
    def in_stock(self):
        """Проверка наличия товара."""
        return self.quantity > 0


def generate_purchase_code():
    """
    Генерация уникального кода покупки.
    Формат: MARS-XXXX-XXXX-XXXX (где X — буквы и цифры)
    Используем UUID для гарантии уникальности.
    """
    # Используем UUID4 для гарантии уникальности
    code_uuid = str(uuid.uuid4()).upper().replace('-', '')
    # Формируем код: MARS-XXXX-XXXX-XXXX
    return f"MARS-{code_uuid[:4]}-{code_uuid[4:8]}-{code_uuid[8:12]}"


class ShopPurchase(models.Model):
    """
    Модель покупки в магазине.
    Каждая покупка имеет УНИКАЛЬНЫЙ код (purchase_code),
    который генерируется автоматически.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Можно забрать'
        SOLD = 'SOLD', 'Получено'
        RETURNED = 'RETURNED', 'Возвращено'
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shop_purchases',
        verbose_name='Студент'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchases',
        verbose_name='Товар'
    )
    purchase_code = models.CharField(
        max_length=20,
        unique=True,
        default=generate_purchase_code,
        verbose_name='Код покупки'
    )
    price = models.PositiveIntegerField(verbose_name='Цена на момент покупки')
    product_name = models.CharField(max_length=200, verbose_name='Название товара')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата покупки')
    
    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.product_name} ({self.purchase_code})"
