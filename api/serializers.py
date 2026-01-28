"""
Сериализаторы DRF для Mars Devs.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from .models import (
    User, Course, Task, TaskSubmission,
    CoinTransaction, TypingResult, ChessGameHistory,
    ChessGame, ChessInvite, Product, ShopPurchase
)
import secrets
import string


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса."""
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'name', 'time', 'day_of_week', 'day_of_week_display', 'description']


class UserSerializer(serializers.ModelSerializer):
    """Базовый сериализатор пользователя."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    student_group_display = serializers.CharField(source='get_student_group_display', read_only=True)
    assigned_courses = CourseSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'phone', 'avatar', 'nickname',
            'student_group', 'student_group_display', 'balance',
            'assigned_courses', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'role', 'balance', 'date_joined']


class LoginSerializer(serializers.Serializer):
    """Сериализатор для логина."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    expected_role = serializers.ChoiceField(
        choices=['TEACHER', 'STUDENT'],
        required=False,
        help_text='Ожидаемая роль пользователя'
    )
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        expected_role = data.get('expected_role')
        
        if username and password:
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Неверный логин или пароль.')
            
            if not user.is_active:
                raise serializers.ValidationError('Аккаунт деактивирован.')
            
            # Проверяем соответствие роли
            if expected_role:
                if expected_role == 'TEACHER' and user.role != 'TEACHER':
                    raise serializers.ValidationError('Данный аккаунт не является учителем.')
                if expected_role == 'STUDENT' and user.role != 'STUDENT':
                    raise serializers.ValidationError('Данный аккаунт не является студентом.')
            
            data['user'] = user
        else:
            raise serializers.ValidationError('Необходимо указать логин и пароль.')
        
        return data


class StudentCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания студента учителем."""
    generated_username = serializers.CharField(read_only=True)
    generated_password = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'parent_info',
            'student_group', 'generated_username', 'generated_password'
        ]
    
    def generate_credentials(self, first_name, last_name):
        """Генерация логина и пароля для студента."""
        # Генерируем username из имени + случайные цифры
        base = f"{first_name.lower()}"
        if last_name:
            base += f"_{last_name.lower()}"
        # Транслитерация кириллицы
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        username = ''
        for char in base:
            if char in translit_map:
                username += translit_map[char]
            elif char.isalnum() or char == '_':
                username += char
        
        # Добавляем случайные цифры
        username += '_' + ''.join(secrets.choice(string.digits) for _ in range(4))
        
        # Генерируем пароль
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        return username, password
    
    def create(self, validated_data):
        teacher = self.context['request'].user
        
        # Генерируем логин и пароль
        username, password = self.generate_credentials(
            validated_data['first_name'],
            validated_data.get('last_name', '')
        )
        
        # Создаём пользователя
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            parent_info=validated_data.get('parent_info', ''),
            student_group=validated_data.get('student_group', User.StudentGroup.NONE),
            role=User.Role.STUDENT,
            created_by=teacher,
            raw_password=password  # Сохраняем оригинальный пароль для учителя
        )
        
        # Сохраняем пароль для ответа (только один раз)
        user.generated_username = username
        user.generated_password = password
        
        return user
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Добавляем сгенерированные credentials в ответ
        if hasattr(instance, 'generated_username'):
            data['generated_username'] = instance.generated_username
        if hasattr(instance, 'generated_password'):
            data['generated_password'] = instance.generated_password
        return data


class StudentListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка студентов."""
    student_group_display = serializers.CharField(source='get_student_group_display', read_only=True)
    pending_tasks = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'phone',
            'student_group', 'student_group_display', 'balance',
            'avatar', 'parent_info', 'pending_tasks', 'date_joined',
            'raw_password'  # Пароль для просмотра учителем
        ]
    
    def get_pending_tasks(self, obj):
        """Количество заданий на проверке."""
        return obj.task_submissions.filter(status='PENDING').count()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления профиля."""
    class Meta:
        model = User
        fields = ['nickname', 'avatar', 'phone']
    
    def validate_avatar(self, value):
        if value:
            # Проверка размера файла (макс 2MB)
            if value.size > settings.MAX_UPLOAD_SIZE:
                raise serializers.ValidationError(
                    f'Размер файла не должен превышать {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB.'
                )
            # Проверка типа файла
            if value.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise serializers.ValidationError(
                    'Допустимые форматы: JPG, JPEG, PNG.'
                )
        return value


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор задания."""
    target_group_display = serializers.CharField(source='get_target_group_display', read_only=True)
    is_submitted = serializers.SerializerMethodField()
    submission_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'target_group', 'target_group_display',
            'reward_coins', 'is_active', 'deadline', 'created_at',
            'is_submitted', 'submission_status'
        ]
    
    def get_is_submitted(self, obj):
        """Проверяет, отправил ли текущий пользователь это задание."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.submissions.filter(student=request.user).exists()
        return False
    
    def get_submission_status(self, obj):
        """Возвращает статус отправки задания."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            submission = obj.submissions.filter(student=request.user).first()
            if submission:
                return submission.status
        return None


class TaskSubmissionSerializer(serializers.ModelSerializer):
    """Сериализатор отправки задания."""
    task_title = serializers.CharField(source='task.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TaskSubmission
        fields = [
            'id', 'task', 'task_title', 'student', 'student_name',
            'text_answer', 'file_answer', 'status', 'status_display',
            'grade', 'teacher_comment', 'coins_awarded',
            'submitted_at', 'reviewed_at'
        ]
        read_only_fields = [
            'id', 'student', 'status', 'grade', 'teacher_comment',
            'coins_awarded', 'submitted_at', 'reviewed_at'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username


class TaskSubmissionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания отправки задания."""
    class Meta:
        model = TaskSubmission
        fields = ['task', 'text_answer', 'file_answer']
    
    def validate(self, data):
        user = self.context['request'].user
        task = data['task']
        
        # Проверяем, что студент ещё не отправлял это задание
        if TaskSubmission.objects.filter(task=task, student=user).exists():
            raise serializers.ValidationError('Вы уже отправили это задание.')
        
        # Проверяем, что задание доступно для группы студента
        if task.target_group != 'ALL' and task.target_group != user.student_group:
            raise serializers.ValidationError('Это задание недоступно для вашей группы.')
        
        # Проверяем, что есть хотя бы текст или файл
        if not data.get('text_answer') and not data.get('file_answer'):
            raise serializers.ValidationError('Необходимо предоставить текстовый ответ или файл.')
        
        return data
    
    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)


class TaskSubmissionReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для проверки задания учителем."""
    class Meta:
        model = TaskSubmission
        fields = ['status', 'grade', 'teacher_comment', 'coins_awarded']
    
    def validate_status(self, value):
        if value not in ['APPROVED', 'REJECTED']:
            raise serializers.ValidationError('Статус должен быть APPROVED или REJECTED.')
        return value


class CoinTransactionSerializer(serializers.ModelSerializer):
    """Сериализатор транзакции монет."""
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CoinTransaction
        fields = [
            'id', 'amount', 'reason', 'source', 'source_display',
            'balance_after', 'created_at', 'created_by_name'
        ]
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class CoinOperationSerializer(serializers.Serializer):
    """Сериализатор для операции с монетами."""
    amount = serializers.IntegerField()
    reason = serializers.CharField(max_length=200)
    
    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError('Сумма не может быть равна нулю.')
        return value


class TypingResultSerializer(serializers.ModelSerializer):
    """Сериализатор результата печати."""
    class Meta:
        model = TypingResult
        fields = [
            'id', 'wpm', 'accuracy', 'characters_typed',
            'errors', 'duration_seconds', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChessGameHistorySerializer(serializers.ModelSerializer):
    """Сериализатор истории шахматных игр."""
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ChessGameHistory
        fields = [
            'id', 'user', 'user_name', 'opponent_name', 'result',
            'result_display', 'notes', 'played_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ChessGameCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания записи о шахматной игре (учителем вручную)."""
    class Meta:
        model = ChessGameHistory
        fields = ['user', 'opponent_name', 'result', 'notes', 'played_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# ================== Шахматы (реальная игра) ==================

class ChessGameSerializer(serializers.ModelSerializer):
    """Сериализатор шахматной партии."""
    player_name = serializers.SerializerMethodField()
    opponent_name = serializers.SerializerMethodField()
    opponent_display = serializers.CharField(source='get_opponent_display', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ChessGame
        fields = [
            'id', 'player', 'player_name', 'opponent_type', 'bot_level',
            'opponent', 'opponent_name', 'opponent_display',
            'status', 'status_display', 'result', 'result_display',
            'coins_earned', 'fen_position', 'last_move', 'current_turn',
            'white_player', 'started_at', 'finished_at', 'updated_at'
        ]
        read_only_fields = ['id', 'player', 'started_at', 'finished_at', 'updated_at']
    
    def get_player_name(self, obj):
        return obj.player.get_full_name() or obj.player.username
    
    def get_opponent_name(self, obj):
        if obj.opponent:
            return obj.opponent.get_full_name() or obj.opponent.username
        return None


class ChessGameStartSerializer(serializers.Serializer):
    """Сериализатор для начала шахматной партии."""
    opponent_type = serializers.ChoiceField(choices=['BOT', 'STUDENT'])
    bot_level = serializers.ChoiceField(choices=['easy', 'medium', 'hard'], required=False)
    
    def validate(self, data):
        if data['opponent_type'] == 'BOT' and not data.get('bot_level'):
            raise serializers.ValidationError('Необходимо указать уровень бота.')
        return data


class ChessGameFinishSerializer(serializers.Serializer):
    """Сериализатор для завершения шахматной партии."""
    game_id = serializers.IntegerField()
    result = serializers.ChoiceField(choices=['WIN', 'LOSE', 'DRAW'])
    
    def validate_game_id(self, value):
        try:
            game = ChessGame.objects.get(pk=value)
            if game.status != ChessGame.Status.IN_PROGRESS:
                raise serializers.ValidationError('Игра уже завершена.')
            self.game = game
        except ChessGame.DoesNotExist:
            raise serializers.ValidationError('Игра не найдена.')
        return value


class ChessGameMoveSerializer(serializers.Serializer):
    """Сериализатор для хода в шахматной партии (PvP)."""
    game_id = serializers.IntegerField()
    fen = serializers.CharField(max_length=100)
    move = serializers.CharField(max_length=10)


class OnlineStudentSerializer(serializers.ModelSerializer):
    """Сериализатор для списка онлайн студентов."""
    display_name = serializers.SerializerMethodField()
    has_pending_invite = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'display_name', 
                  'avatar', 'has_pending_invite']
    
    def get_display_name(self, obj):
        return obj.get_full_name() or obj.nickname or obj.username
    
    def get_has_pending_invite(self, obj):
        """Проверяет, есть ли уже ожидающее приглашение от текущего пользователя."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ChessInvite.objects.filter(
                from_player=request.user,
                to_player=obj,
                status=ChessInvite.Status.PENDING
            ).exists()
        return False


class ChessInviteSerializer(serializers.ModelSerializer):
    """Сериализатор приглашения в шахматы."""
    from_player_name = serializers.SerializerMethodField()
    to_player_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ChessInvite
        fields = [
            'id', 'from_player', 'from_player_name', 
            'to_player', 'to_player_name',
            'status', 'status_display', 'game',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'from_player', 'status', 'game', 'created_at', 'updated_at']
    
    def get_from_player_name(self, obj):
        return obj.from_player.get_full_name() or obj.from_player.username
    
    def get_to_player_name(self, obj):
        return obj.to_player.get_full_name() or obj.to_player.username


class ChessInviteCreateSerializer(serializers.Serializer):
    """Сериализатор для создания приглашения."""
    to_player_id = serializers.IntegerField()
    
    def validate_to_player_id(self, value):
        try:
            player = User.objects.get(pk=value, role=User.Role.STUDENT)
            if player == self.context['request'].user:
                raise serializers.ValidationError('Нельзя пригласить самого себя.')
            self.to_player = player
        except User.DoesNotExist:
            raise serializers.ValidationError('Студент не найден.')
        return value


class ChessInviteResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа на приглашение."""
    invite_id = serializers.IntegerField()
    accept = serializers.BooleanField()


class ChessStatsSerializer(serializers.Serializer):
    """Сериализатор статистики шахмат."""
    total_games = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    draws = serializers.IntegerField()
    total_coins_earned = serializers.IntegerField()
    bot_games = serializers.IntegerField()
    pvp_games = serializers.IntegerField()


# ================== Магазин ==================

class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор товара.
    Товар НЕ содержит код — код генерируется при покупке.
    """
    in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'image', 
            'price', 'quantity', 'in_stock', 'is_active', 'created_at'
        ]


class ShopPurchaseSerializer(serializers.ModelSerializer):
    """
    Сериализатор покупки.
    purchase_code — уникальный код, сгенерированный для каждой покупки.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ShopPurchase
        fields = [
            'id', 'product_name', 'purchase_code', 
            'price', 'status', 'status_display', 'purchased_at'
        ]


class BuyProductSerializer(serializers.Serializer):
    """Сериализатор для покупки товара."""
    product_id = serializers.IntegerField()
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value, is_active=True)
            self.product = product
        except Product.DoesNotExist:
            raise serializers.ValidationError('Товар не найден или недоступен.')
        return value
