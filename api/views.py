"""
API views для Mars Devs.
"""
from rest_framework import status, generics, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db import transaction, models
from django.db.models import Q, Sum

from .models import (
    User, Course, Task, TaskSubmission,
    CoinTransaction, TypingResult, ChessGameHistory,
    ChessGame, ChessInvite, Product, ShopPurchase
)
from .serializers import (
    UserSerializer, LoginSerializer, StudentCreateSerializer,
    StudentListSerializer, ProfileUpdateSerializer,
    TaskSerializer, TaskSubmissionSerializer,
    TaskSubmissionCreateSerializer, TaskSubmissionReviewSerializer,
    CoinTransactionSerializer, CoinOperationSerializer,
    TypingResultSerializer, ChessGameHistorySerializer,
    ChessGameCreateSerializer, CourseSerializer,
    # Сериализаторы для шахмат
    ChessGameSerializer, ChessGameStartSerializer, ChessGameFinishSerializer,
    ChessGameMoveSerializer, OnlineStudentSerializer, ChessInviteSerializer,
    ChessInviteCreateSerializer, ChessInviteResponseSerializer,
    # Сериализаторы для магазина
    ProductSerializer, ShopPurchaseSerializer, BuyProductSerializer
)
from .permissions import IsTeacher, IsStudent, IsTeacherOrAdmin, IsOwnerOrTeacher
from datetime import timedelta


class LoginView(APIView):
    """
    Эндпоинт для авторизации пользователей.
    Возвращает JWT токены и информацию о пользователе.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Генерируем JWT токены
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class ProfileView(APIView):
    """
    Эндпоинт для получения и обновления профиля текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request):
        """Получить профиль текущего пользователя."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        """Обновить профиль (nickname, avatar, phone)."""
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(UserSerializer(request.user).data)


class StudentListCreateView(APIView):
    """
    Эндпоинт для работы со студентами (для учителей).
    GET - список студентов
    POST - создание нового студента
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get(self, request):
        """Получить список студентов."""
        # Учитель видит студентов, которых он создал
        students = User.objects.filter(
            role=User.Role.STUDENT,
            created_by=request.user
        ).order_by('-date_joined')
        
        serializer = StudentListSerializer(students, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Создать нового студента."""
        serializer = StudentCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        
        return Response({
            'message': 'Студент успешно создан',
            'student': StudentListSerializer(student).data,
            'credentials': {
                'username': student.generated_username,
                'password': student.generated_password
            }
        }, status=status.HTTP_201_CREATED)


class StudentDetailView(APIView):
    """
    Эндпоинт для работы с конкретным студентом.
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_object(self, pk):
        try:
            return User.objects.get(
                pk=pk,
                role=User.Role.STUDENT,
                created_by=self.request.user
            )
        except User.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """Получить информацию о студенте."""
        student = self.get_object(pk)
        if not student:
            return Response(
                {'error': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = StudentListSerializer(student)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        """Обновить информацию о студенте."""
        student = self.get_object(pk)
        if not student:
            return Response(
                {'error': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Разрешаем обновлять только определённые поля
        allowed_fields = ['first_name', 'last_name', 'phone', 'parent_info', 'student_group']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        for field, value in update_data.items():
            setattr(student, field, value)
        student.save()
        
        return Response(StudentListSerializer(student).data)


class StudentCoinsView(APIView):
    """
    Эндпоинт для управления монетами студента (для учителей).
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_student(self, pk):
        try:
            return User.objects.get(
                pk=pk,
                role=User.Role.STUDENT,
                created_by=self.request.user
            )
        except User.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """Получить историю транзакций студента."""
        student = self.get_student(pk)
        if not student:
            return Response(
                {'error': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        transactions = student.coin_transactions.all()[:50]
        serializer = CoinTransactionSerializer(transactions, many=True)
        
        return Response({
            'balance': student.balance,
            'transactions': serializer.data
        })
    
    @transaction.atomic
    def post(self, request, pk):
        """Начислить/списать монеты студенту."""
        student = self.get_student(pk)
        if not student:
            return Response(
                {'error': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CoinOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        reason = serializer.validated_data['reason']
        
        # Проверяем, что баланс не станет отрицательным
        new_balance = student.balance + amount
        if new_balance < 0:
            return Response(
                {'error': 'Недостаточно монет на балансе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Обновляем баланс
        student.balance = new_balance
        student.save()
        
        # Создаём запись о транзакции
        transaction = CoinTransaction.objects.create(
            user=student,
            amount=amount,
            reason=reason,
            source=CoinTransaction.Source.TEACHER,
            balance_after=new_balance,
            created_by=request.user
        )
        
        return Response({
            'message': 'Операция выполнена успешно',
            'new_balance': new_balance,
            'transaction': CoinTransactionSerializer(transaction).data
        })


class TaskListView(APIView):
    """
    Эндпоинт для списка заданий.
    Студенты видят задания своей группы.
    Учителя видят все задания.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role == User.Role.TEACHER:
            # Учитель видит все задания
            tasks = Task.objects.filter(is_active=True)
        else:
            # Студент видит задания своей группы
            tasks = Task.objects.filter(
                is_active=True
            ).filter(
                Q(target_group=user.student_group) | Q(target_group='ALL')
            )
        
        serializer = TaskSerializer(
            tasks,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class TaskSubmitView(APIView):
    """
    Эндпоинт для отправки выполненного задания (для студентов).
    """
    permission_classes = [IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response(
                {'error': 'Задание не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем доступность задания для группы студента
        if task.target_group != 'ALL' and task.target_group != request.user.student_group:
            return Response(
                {'error': 'Это задание недоступно для вашей группы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['task'] = task.id
        
        serializer = TaskSubmissionCreateSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        
        return Response({
            'message': 'Задание успешно отправлено',
            'submission': TaskSubmissionSerializer(submission).data
        }, status=status.HTTP_201_CREATED)


class TaskSubmissionsListView(APIView):
    """
    Эндпоинт для просмотра отправок заданий (для учителей).
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get(self, request):
        # Получаем отправки от студентов учителя
        student_ids = User.objects.filter(
            role=User.Role.STUDENT,
            created_by=request.user
        ).values_list('id', flat=True)
        
        status_filter = request.query_params.get('status')
        
        submissions = TaskSubmission.objects.filter(
            student_id__in=student_ids
        ).select_related('task', 'student')
        
        if status_filter:
            submissions = submissions.filter(status=status_filter)
        
        serializer = TaskSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class TaskSubmissionReviewView(APIView):
    """
    Эндпоинт для проверки задания учителем.
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    @transaction.atomic
    def post(self, request, submission_id):
        try:
            submission = TaskSubmission.objects.select_related(
                'student', 'task'
            ).get(pk=submission_id)
        except TaskSubmission.DoesNotExist:
            return Response(
                {'error': 'Отправка не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем, что студент принадлежит этому учителю
        if submission.student.created_by != request.user:
            return Response(
                {'error': 'Нет доступа к этой отправке'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TaskSubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Обновляем отправку
        submission.status = serializer.validated_data['status']
        submission.grade = serializer.validated_data.get('grade')
        submission.teacher_comment = serializer.validated_data.get('teacher_comment', '')
        submission.coins_awarded = serializer.validated_data.get('coins_awarded', 0)
        submission.reviewed_at = timezone.now()
        submission.reviewed_by = request.user
        submission.save()
        
        # Если одобрено и есть награда, начисляем монеты
        if submission.status == 'APPROVED' and submission.coins_awarded > 0:
            student = submission.student
            student.balance += submission.coins_awarded
            student.save()
            
            CoinTransaction.objects.create(
                user=student,
                amount=submission.coins_awarded,
                reason=f'За задание: {submission.task.title}',
                source=CoinTransaction.Source.TASK,
                balance_after=student.balance,
                created_by=request.user
            )
        
        return Response({
            'message': 'Задание проверено',
            'submission': TaskSubmissionSerializer(submission).data
        })


class MySubmissionsView(APIView):
    """
    Эндпоинт для получения своих отправок заданий (для студентов).
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        submissions = request.user.task_submissions.select_related('task').all()
        serializer = TaskSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class MyCoinTransactionsView(APIView):
    """
    Эндпоинт для получения своих транзакций монет.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        transactions = request.user.coin_transactions.all()[:100]
        serializer = CoinTransactionSerializer(transactions, many=True)
        return Response({
            'balance': request.user.balance,
            'transactions': serializer.data
        })


class TypingResultsView(APIView):
    """
    Эндпоинт для результатов теста печати.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить свои результаты печати."""
        results = request.user.typing_results.all()[:50]
        serializer = TypingResultSerializer(results, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Сохранить результат теста печати."""
        serializer = TypingResultSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response(
            TypingResultSerializer(result).data,
            status=status.HTTP_201_CREATED
        )


class ChessHistoryView(APIView):
    """
    Эндпоинт для истории шахматных игр.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить историю шахматных игр пользователя."""
        user_id = request.query_params.get('user_id')
        
        if user_id and request.user.role == User.Role.TEACHER:
            # Учитель может смотреть историю своих студентов
            games = ChessGameHistory.objects.filter(
                user_id=user_id,
                user__created_by=request.user
            )
        else:
            games = request.user.chess_games.all()
        
        serializer = ChessGameHistorySerializer(games, many=True)
        
        # Считаем статистику
        wins = games.filter(result='WIN').count()
        losses = games.filter(result='LOSS').count()
        draws = games.filter(result='DRAW').count()
        
        return Response({
            'games': serializer.data,
            'stats': {
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'total': games.count()
            }
        })
    
    def post(self, request):
        """Добавить запись о шахматной игре (для учителей)."""
        if request.user.role != User.Role.TEACHER:
            return Response(
                {'error': 'Только учителя могут добавлять записи'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChessGameCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        game = serializer.save()
        
        return Response(
            ChessGameHistorySerializer(game).data,
            status=status.HTTP_201_CREATED
        )


class CourseListView(generics.ListAPIView):
    """
    Эндпоинт для списка курсов.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CourseSerializer
    queryset = Course.objects.all()


class TeacherStatsView(APIView):
    """
    Эндпоинт для статистики учителя.
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get(self, request):
        teacher = request.user
        
        # Количество студентов
        students_count = User.objects.filter(
            role=User.Role.STUDENT,
            created_by=teacher
        ).count()
        
        # Задания на проверке
        student_ids = User.objects.filter(
            role=User.Role.STUDENT,
            created_by=teacher
        ).values_list('id', flat=True)
        
        pending_submissions = TaskSubmission.objects.filter(
            student_id__in=student_ids,
            status='PENDING'
        ).count()
        
        # Проверенные за сегодня
        from django.utils import timezone
        today = timezone.now().date()
        reviewed_today = TaskSubmission.objects.filter(
            reviewed_by=teacher,
            reviewed_at__date=today
        ).count()
        
        return Response({
            'students_count': students_count,
            'pending_submissions': pending_submissions,
            'reviewed_today': reviewed_today,
            'courses': CourseSerializer(teacher.assigned_courses.all(), many=True).data
        })


# ================== Шахматы (реальная игра) ==================

# Награды за шахматы
CHESS_REWARDS = {
    'BOT': {
        'easy': {'WIN': 45, 'DRAW': 10, 'LOSE': 0},
        'medium': {'WIN': 75, 'DRAW': 20, 'LOSE': 0},
        'hard': {'WIN': 100, 'DRAW': 30, 'LOSE': 0},
    },
    'STUDENT': {
        'WIN': 50,
        'DRAW': 20,
        'LOSE': 0
    }
}


class ChessStartGameView(APIView):
    """
    Начать новую шахматную партию.
    POST /api/chess/start/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def post(self, request):
        serializer = ChessGameStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        opponent_type = serializer.validated_data['opponent_type']
        bot_level = serializer.validated_data.get('bot_level')
        
        # Создаём новую игру
        game = ChessGame.objects.create(
            player=request.user,
            opponent_type=opponent_type,
            bot_level=bot_level if opponent_type == 'BOT' else None,
            white_player=request.user,  # Игрок всегда играет белыми против бота
            status=ChessGame.Status.IN_PROGRESS
        )
        
        return Response({
            'message': 'Игра начата',
            'game': ChessGameSerializer(game).data
        }, status=status.HTTP_201_CREATED)


class ChessFinishGameView(APIView):
    """
    Завершить шахматную партию и начислить награду.
    POST /api/chess/finish/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    @transaction.atomic
    def post(self, request):
        serializer = ChessGameFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        game = serializer.game
        result = serializer.validated_data['result']
        
        # Проверяем, что игрок - участник игры
        if game.player != request.user and game.opponent != request.user:
            return Response(
                {'error': 'Вы не являетесь участником этой игры'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Определяем награду
        if game.opponent_type == ChessGame.OpponentType.BOT:
            coins = CHESS_REWARDS['BOT'][game.bot_level][result]
        else:
            coins = CHESS_REWARDS['STUDENT'][result]
        
        # Обновляем игру
        game.result = result
        game.status = ChessGame.Status.FINISHED
        game.coins_earned = coins
        game.finished_at = timezone.now()
        game.save()
        
        # Начисляем монеты если победа или ничья
        if coins > 0:
            user = request.user
            user.balance += coins
            user.save()
            
            # Создаём запись о транзакции
            opponent_name = game.get_opponent_display()
            CoinTransaction.objects.create(
                user=user,
                amount=coins,
                reason=f'Шахматы: {game.get_result_display()} против {opponent_name}',
                source=CoinTransaction.Source.CHESS,
                balance_after=user.balance
            )
        
        return Response({
            'message': 'Игра завершена',
            'game': ChessGameSerializer(game).data,
            'coins_earned': coins,
            'new_balance': request.user.balance
        })


class ChessMyGamesView(APIView):
    """
    Получить свои шахматные партии и статистику.
    GET /api/chess/my-games/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Получаем все завершённые игры пользователя
        games = ChessGame.objects.filter(
            Q(player=request.user) | Q(opponent=request.user),
            status=ChessGame.Status.FINISHED
        ).order_by('-finished_at')[:50]
        
        # Считаем статистику
        all_games = ChessGame.objects.filter(
            Q(player=request.user) | Q(opponent=request.user),
            status=ChessGame.Status.FINISHED
        )
        
        wins = all_games.filter(player=request.user, result='WIN').count()
        wins += all_games.filter(opponent=request.user, result='LOSE').count()
        
        losses = all_games.filter(player=request.user, result='LOSE').count()
        losses += all_games.filter(opponent=request.user, result='WIN').count()
        
        draws = all_games.filter(result='DRAW').count()
        
        total_coins = all_games.filter(player=request.user).aggregate(
            total=models.Sum('coins_earned')
        )['total'] or 0
        
        bot_games = all_games.filter(opponent_type='BOT').count()
        pvp_games = all_games.filter(opponent_type='STUDENT').count()
        
        return Response({
            'games': ChessGameSerializer(games, many=True).data,
            'stats': {
                'total_games': all_games.count(),
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'total_coins_earned': total_coins,
                'bot_games': bot_games,
                'pvp_games': pvp_games
            }
        })


class ChessOnlineStudentsView(APIView):
    """
    Получить список студентов онлайн (для PvP).
    Используем простой polling - студент считается онлайн,
    если был активен в последние 5 минут.
    GET /api/chess/online-students/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        # Получаем студентов, активных в последние 5 минут
        # В реальном приложении здесь была бы более сложная логика
        # Пока просто возвращаем всех студентов кроме текущего
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        
        # Все студенты (в простой версии - все студенты)
        students = User.objects.filter(
            role=User.Role.STUDENT
        ).exclude(pk=request.user.pk).order_by('username')[:20]
        
        serializer = OnlineStudentSerializer(
            students, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class ChessInviteView(APIView):
    """
    Отправить приглашение в шахматы другому студенту.
    POST /api/chess/invite/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def post(self, request):
        serializer = ChessInviteCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        to_player = serializer.to_player
        
        # Проверяем, нет ли уже активного приглашения
        existing = ChessInvite.objects.filter(
            from_player=request.user,
            to_player=to_player,
            status=ChessInvite.Status.PENDING
        ).first()
        
        if existing:
            return Response(
                {'error': 'Приглашение уже отправлено'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаём приглашение
        invite = ChessInvite.objects.create(
            from_player=request.user,
            to_player=to_player
        )
        
        return Response({
            'message': 'Приглашение отправлено',
            'invite': ChessInviteSerializer(invite).data
        }, status=status.HTTP_201_CREATED)


class ChessMyInvitesView(APIView):
    """
    Получить свои приглашения (входящие и исходящие).
    GET /api/chess/my-invites/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        # Входящие ожидающие приглашения
        incoming = ChessInvite.objects.filter(
            to_player=request.user,
            status=ChessInvite.Status.PENDING
        ).order_by('-created_at')
        
        # Исходящие ожидающие приглашения
        outgoing = ChessInvite.objects.filter(
            from_player=request.user,
            status=ChessInvite.Status.PENDING
        ).order_by('-created_at')
        
        return Response({
            'incoming': ChessInviteSerializer(incoming, many=True).data,
            'outgoing': ChessInviteSerializer(outgoing, many=True).data
        })


class ChessRespondInviteView(APIView):
    """
    Ответить на приглашение (принять/отклонить).
    POST /api/chess/respond-invite/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    @transaction.atomic
    def post(self, request):
        serializer = ChessInviteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invite_id = serializer.validated_data['invite_id']
        accept = serializer.validated_data['accept']
        
        try:
            invite = ChessInvite.objects.get(
                pk=invite_id,
                to_player=request.user,
                status=ChessInvite.Status.PENDING
            )
        except ChessInvite.DoesNotExist:
            return Response(
                {'error': 'Приглашение не найдено или уже обработано'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if accept:
            # Принимаем приглашение - создаём игру
            import random
            
            # Случайно определяем кто играет белыми
            if random.choice([True, False]):
                white_player = invite.from_player
                black_player = invite.to_player
            else:
                white_player = invite.to_player
                black_player = invite.from_player
            
            game = ChessGame.objects.create(
                player=invite.from_player,
                opponent_type=ChessGame.OpponentType.STUDENT,
                opponent=invite.to_player,
                white_player=white_player,
                status=ChessGame.Status.IN_PROGRESS
            )
            
            invite.status = ChessInvite.Status.ACCEPTED
            invite.game = game
            invite.save()
            
            return Response({
                'message': 'Приглашение принято',
                'invite': ChessInviteSerializer(invite).data,
                'game': ChessGameSerializer(game).data
            })
        else:
            # Отклоняем приглашение
            invite.status = ChessInvite.Status.DECLINED
            invite.save()
            
            return Response({
                'message': 'Приглашение отклонено',
                'invite': ChessInviteSerializer(invite).data
            })


class ChessGameStateView(APIView):
    """
    Получить/обновить состояние игры (для PvP polling).
    GET /api/chess/game/<game_id>/
    POST /api/chess/game/<game_id>/ - сделать ход
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_game(self, game_id, user):
        try:
            game = ChessGame.objects.get(pk=game_id)
            if game.player != user and game.opponent != user:
                return None
            return game
        except ChessGame.DoesNotExist:
            return None
    
    def get(self, request, game_id):
        """Получить текущее состояние игры."""
        game = self.get_game(game_id, request.user)
        if not game:
            return Response(
                {'error': 'Игра не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Определяем цвет игрока
        player_color = 'white' if game.white_player == request.user else 'black'
        is_my_turn = game.current_turn == player_color
        
        return Response({
            'game': ChessGameSerializer(game).data,
            'player_color': player_color,
            'is_my_turn': is_my_turn
        })
    
    def post(self, request, game_id):
        """Сделать ход в игре."""
        game = self.get_game(game_id, request.user)
        if not game:
            return Response(
                {'error': 'Игра не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if game.status != ChessGame.Status.IN_PROGRESS:
            return Response(
                {'error': 'Игра уже завершена'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что это ход игрока
        player_color = 'white' if game.white_player == request.user else 'black'
        if game.current_turn != player_color:
            return Response(
                {'error': 'Сейчас не ваш ход'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем данные хода
        fen = request.data.get('fen')
        move = request.data.get('move')
        
        if not fen or not move:
            return Response(
                {'error': 'Необходимо указать fen и move'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Обновляем состояние игры
        game.fen_position = fen
        game.last_move = move
        game.current_turn = 'black' if player_color == 'white' else 'white'
        game.save()
        
        return Response({
            'message': 'Ход сделан',
            'game': ChessGameSerializer(game).data
        })


class ChessCancelInviteView(APIView):
    """
    Отменить своё приглашение.
    POST /api/chess/cancel-invite/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def post(self, request):
        invite_id = request.data.get('invite_id')
        
        try:
            invite = ChessInvite.objects.get(
                pk=invite_id,
                from_player=request.user,
                status=ChessInvite.Status.PENDING
            )
        except ChessInvite.DoesNotExist:
            return Response(
                {'error': 'Приглашение не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        invite.status = ChessInvite.Status.EXPIRED
        invite.save()
        
        return Response({'message': 'Приглашение отменено'})


# ================== Магазин ==================

class ShopProductsView(APIView):
    """
    Список товаров в магазине.
    GET /api/shop/products/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        # Только активные товары
        products = Product.objects.filter(is_active=True).order_by('-created_at')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ShopBuyView(APIView):
    """
    Покупка товара.
    POST /api/shop/buy/
    
    Логика:
    - Проверить, что пользователь = STUDENT
    - Проверить, что товар активен
    - Проверить наличие товара (quantity > 0)
    - Проверить баланс coin
    - Списать coin
    - Уменьшить quantity на 1
    - Создать ShopPurchase с автоматически сгенерированным purchase_code
    - Вернуть purchase_code в ответе
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    @transaction.atomic
    def post(self, request):
        serializer = BuyProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Блокируем товар для атомарной операции
        product = Product.objects.select_for_update().get(pk=serializer.product.pk)
        user = request.user
        
        # Проверяем наличие товара
        if product.quantity <= 0:
            return Response(
                {'error': 'Товар закончился'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем баланс
        if user.balance < product.price:
            return Response(
                {'error': 'Недостаточно монет для покупки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Списываем монеты
        user.balance -= product.price
        user.save()
        
        # Уменьшаем количество товара
        product.quantity -= 1
        product.save()
        
        # Создаём запись о покупке (purchase_code генерируется автоматически)
        purchase = ShopPurchase.objects.create(
            student=user,
            product=product,
            price=product.price,
            product_name=product.name
        )
        
        # Создаём транзакцию монет
        CoinTransaction.objects.create(
            user=user,
            amount=-product.price,
            reason=f'Покупка: {product.name}',
            source=CoinTransaction.Source.OTHER,
            balance_after=user.balance
        )
        
        # Возвращаем успешный ответ с кодом покупки
        return Response({
            'success': True,
            'purchase_code': purchase.purchase_code,
            'product_name': product.name,
            'price': product.price,
            'new_balance': user.balance
        })


class ShopPurchaseHistoryView(APIView):
    """
    История покупок студента.
    GET /api/shop/purchases/
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        purchases = request.user.shop_purchases.all()[:50]
        serializer = ShopPurchaseSerializer(purchases, many=True)
        return Response(serializer.data)
