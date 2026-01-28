"""
Конфигурация админ-панели Django для Mars Devs.
Админ может создавать учителей, курсы и задания через эту панель.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import (
    User, Course, Task, TaskSubmission, 
    CoinTransaction, TypingResult, ChessGameHistory,
    ChessGame, ChessInvite, Product, ShopPurchase
)


# Кастомные формы для создания пользователей
class TeacherCreationForm(UserCreationForm):
    """Форма для создания учителя через админ-панель."""
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Кастомная форма редактирования пользователя."""
    class Meta(UserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для пользователей."""
    form = CustomUserChangeForm
    add_form = UserCreationForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'balance', 'is_active')
    list_filter = ('role', 'is_active', 'student_group')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone', 'nickname', 'avatar')}),
        ('Роль и группа', {'fields': ('role', 'student_group', 'assigned_courses')}),
        ('Студент', {'fields': ('parent_info', 'balance', 'created_by')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'first_name', 'last_name', 'email', 'phone'),
        }),
    )
    
    filter_horizontal = ('assigned_courses', 'groups', 'user_permissions')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


# Действие для создания учителя
@admin.action(description='Создать учителя')
def create_teacher_action(modeladmin, request, queryset):
    """Действие для быстрого создания учителя."""
    pass


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Админка для курсов."""
    list_display = ('name', 'day_of_week', 'time', 'get_teachers', 'created_at')
    list_filter = ('day_of_week',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def get_teachers(self, obj):
        """Получить список учителей курса."""
        teachers = obj.teachers.all()
        return ', '.join([t.get_full_name() or t.username for t in teachers]) or 'Не назначен'
    get_teachers.short_description = 'Преподаватели'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Админка для заданий."""
    list_display = ('title', 'target_group', 'reward_coins', 'is_active', 'deadline', 'created_at')
    list_filter = ('target_group', 'is_active')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'


@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    """Админка для отправок заданий."""
    list_display = ('task', 'student', 'status', 'grade', 'coins_awarded', 'submitted_at', 'reviewed_by')
    list_filter = ('status', 'submitted_at')
    search_fields = ('task__title', 'student__username', 'student__first_name')
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at',)
    raw_id_fields = ('task', 'student', 'reviewed_by')


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    """Админка для транзакций монет."""
    list_display = ('user', 'amount', 'reason', 'source', 'balance_after', 'created_at', 'created_by')
    list_filter = ('source', 'created_at')
    search_fields = ('user__username', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'created_by')


@admin.register(TypingResult)
class TypingResultAdmin(admin.ModelAdmin):
    """Админка для результатов печати."""
    list_display = ('user', 'wpm', 'accuracy', 'errors', 'duration_seconds', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(ChessGameHistory)
class ChessGameHistoryAdmin(admin.ModelAdmin):
    """Админка для истории шахматных игр (ручная запись)."""
    list_display = ('user', 'opponent_name', 'result', 'played_at', 'created_by')
    list_filter = ('result', 'played_at')
    search_fields = ('user__username', 'opponent_name')
    ordering = ('-played_at',)
    raw_id_fields = ('user', 'created_by')


@admin.register(ChessGame)
class ChessGameAdmin(admin.ModelAdmin):
    """Админка для шахматных партий (реальная игра)."""
    list_display = ('id', 'player', 'opponent_type', 'bot_level', 'opponent', 'status', 'result', 'coins_earned', 'started_at')
    list_filter = ('opponent_type', 'status', 'result', 'bot_level', 'started_at')
    search_fields = ('player__username', 'opponent__username')
    ordering = ('-started_at',)
    readonly_fields = ('started_at', 'finished_at', 'updated_at')
    raw_id_fields = ('player', 'opponent', 'white_player')
    
    fieldsets = (
        ('Игроки', {'fields': ('player', 'opponent_type', 'bot_level', 'opponent', 'white_player')}),
        ('Статус', {'fields': ('status', 'result', 'coins_earned')}),
        ('Позиция', {'fields': ('fen_position', 'last_move', 'current_turn')}),
        ('Время', {'fields': ('started_at', 'finished_at', 'updated_at')}),
    )


@admin.register(ChessInvite)
class ChessInviteAdmin(admin.ModelAdmin):
    """Админка для приглашений в шахматы."""
    list_display = ('id', 'from_player', 'to_player', 'status', 'game', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_player__username', 'to_player__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('from_player', 'to_player', 'game')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Админка для товаров магазина.
    Admin добавляет товар — он виден всем студентам.
    Код НЕ задаётся здесь — он генерируется при покупке.
    """
    list_display = ('name', 'price', 'quantity', 'is_active', 'purchases_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основное', {'fields': ('name', 'description', 'image')}),
        ('Цена и количество', {'fields': ('price', 'quantity')}),
        ('Статус', {'fields': ('is_active',)}),
        ('Информация', {'fields': ('created_at',)}),
    )
    
    def purchases_count(self, obj):
        """Количество покупок этого товара."""
        return obj.purchases.count()
    purchases_count.short_description = 'Куплено раз'


@admin.register(ShopPurchase)
class ShopPurchaseAdmin(admin.ModelAdmin):
    """
    Админка для покупок в магазине.
    Admin может управлять статусом заказа:
    - Продано (SOLD) — товар выдан
    - Вернуть (RETURNED) — возврат coin студенту
    """
    list_display = ('purchase_code', 'student', 'product_name', 'price', 'status_display', 'purchased_at')
    list_filter = ('status', 'purchased_at')
    search_fields = ('student__username', 'product_name', 'purchase_code')
    ordering = ('-purchased_at',)
    readonly_fields = ('student', 'product', 'purchase_code', 'price', 'product_name', 'status', 'purchased_at')
    actions = ['mark_as_sold', 'mark_as_returned']
    
    def status_display(self, obj):
        """Отображение статуса с иконкой."""
        icons = {
            'PENDING': '🟡',
            'SOLD': '✅',
            'RETURNED': '🔴',
        }
        return f"{icons.get(obj.status, '')} {obj.get_status_display()}"
    status_display.short_description = 'Статус'
    
    def has_add_permission(self, request):
        """Запрещаем создание покупок через admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Разрешаем просмотр, но не редактирование полей."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление покупок."""
        return False
    
    @admin.action(description='✅ Отметить как ПРОДАНО')
    def mark_as_sold(self, request, queryset):
        """Отметить выбранные покупки как проданные."""
        # Фильтруем только PENDING
        pending = queryset.filter(status=ShopPurchase.Status.PENDING)
        count = pending.update(status=ShopPurchase.Status.SOLD)
        self.message_user(request, f'Отмечено как продано: {count} заказов')
    
    @admin.action(description='🔴 ВЕРНУТЬ (возврат coin)')
    def mark_as_returned(self, request, queryset):
        """
        Вернуть coin студенту и отметить как возвращённые.
        Работает только для PENDING и SOLD статусов.
        """
        from django.db import transaction
        from .models import CoinTransaction
        
        # Фильтруем только те, которые можно вернуть (не RETURNED)
        returnable = queryset.exclude(status=ShopPurchase.Status.RETURNED)
        
        returned_count = 0
        for purchase in returnable:
            with transaction.atomic():
                # Возвращаем coin студенту
                student = purchase.student
                student.balance += purchase.price
                student.save()
                
                # Создаём транзакцию о возврате
                CoinTransaction.objects.create(
                    user=student,
                    amount=purchase.price,
                    reason=f'Возврат за: {purchase.product_name}',
                    source=CoinTransaction.Source.OTHER,
                    balance_after=student.balance,
                    created_by=request.user
                )
                
                # Обновляем статус покупки
                purchase.status = ShopPurchase.Status.RETURNED
                purchase.save()
                
                returned_count += 1
        
        self.message_user(request, f'Возвращено: {returned_count} заказов. Coin возвращены студентам.')


# Настройка заголовка админ-панели
admin.site.site_header = 'Mars Devs - Панель администратора'
admin.site.site_title = 'Mars Devs Admin'
admin.site.index_title = 'Управление платформой'
