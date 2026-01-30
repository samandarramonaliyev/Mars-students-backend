"""
Тесты для API Mars Devs.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Course, Task, CoinTransaction, ChessGame
from django.utils import timezone

User = get_user_model()


class AuthenticationTests(APITestCase):
    """Тесты аутентификации."""

    def setUp(self):
        """Создание тестовых пользователей."""
        self.teacher = User.objects.create_user(
            username='test_teacher',
            password='testpass123',
            first_name='Тест',
            last_name='Учитель',
            role='TEACHER'
        )
        self.student = User.objects.create_user(
            username='test_student',
            password='testpass123',
            first_name='Тест',
            last_name='Студент',
            role='STUDENT',
            created_by=self.teacher
        )

    def test_login_teacher_success(self):
        """Тест успешного логина учителя."""
        url = reverse('login')
        data = {
            'username': 'test_teacher',
            'password': 'testpass123',
            'expected_role': 'TEACHER'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['role'], 'TEACHER')

    def test_login_student_success(self):
        """Тест успешного логина студента."""
        url = reverse('login')
        data = {
            'username': 'test_student',
            'password': 'testpass123',
            'expected_role': 'STUDENT'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['role'], 'STUDENT')

    def test_login_wrong_password(self):
        """Тест логина с неверным паролем."""
        url = reverse('login')
        data = {
            'username': 'test_teacher',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_wrong_role(self):
        """Тест логина с неверной ролью."""
        url = reverse('login')
        data = {
            'username': 'test_student',
            'password': 'testpass123',
            'expected_role': 'TEACHER'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StudentManagementTests(APITestCase):
    """Тесты управления студентами."""

    def setUp(self):
        """Создание тестовых данных."""
        self.teacher = User.objects.create_user(
            username='test_teacher',
            password='testpass123',
            role='TEACHER'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def test_create_student(self):
        """Тест создания студента учителем."""
        url = reverse('students-list-create')
        data = {
            'first_name': 'Новый',
            'last_name': 'Студент',
            'phone': '+7 (999) 000-00-00',
            'student_group': 'FRONTEND'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('credentials', response.data)
        self.assertIn('username', response.data['credentials'])
        self.assertIn('password', response.data['credentials'])
        
        # Проверяем, что студент создан
        student = User.objects.get(username=response.data['credentials']['username'])
        self.assertEqual(student.role, 'STUDENT')
        self.assertEqual(student.created_by, self.teacher)

    def test_list_students(self):
        """Тест получения списка студентов."""
        # Создаём студента
        student = User.objects.create_user(
            username='student1',
            password='pass123',
            role='STUDENT',
            created_by=self.teacher
        )
        
        url = reverse('students-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class CoinTransactionTests(APITestCase):
    """Тесты операций с монетами."""

    def setUp(self):
        """Создание тестовых данных."""
        self.teacher = User.objects.create_user(
            username='test_teacher',
            password='testpass123',
            role='TEACHER'
        )
        self.student = User.objects.create_user(
            username='test_student',
            password='testpass123',
            role='STUDENT',
            created_by=self.teacher,
            balance=100
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def test_add_coins(self):
        """Тест начисления монет."""
        url = reverse('student-coins', args=[self.student.id])
        data = {
            'amount': 50,
            'reason': 'За хорошую работу'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['new_balance'], 150)
        
        # Проверяем баланс студента
        self.student.refresh_from_db()
        self.assertEqual(self.student.balance, 150)
        
        # Проверяем создание транзакции
        transaction = CoinTransaction.objects.filter(user=self.student).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, 50)

    def test_subtract_coins(self):
        """Тест списания монет."""
        url = reverse('student-coins', args=[self.student.id])
        data = {
            'amount': -30,
            'reason': 'Штраф'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['new_balance'], 70)

    def test_insufficient_balance(self):
        """Тест списания при недостаточном балансе."""
        url = reverse('student-coins', args=[self.student.id])
        data = {
            'amount': -200,
            'reason': 'Большой штраф'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChessMoveTests(APITestCase):
    """Тесты ходов в шахматах."""

    def setUp(self):
        """Создание тестовых данных."""
        self.student1 = User.objects.create_user(
            username='chess_student1',
            password='testpass123',
            role='STUDENT'
        )
        self.student2 = User.objects.create_user(
            username='chess_student2',
            password='testpass123',
            role='STUDENT'
        )
        self.game = ChessGame.objects.create(
            player=self.student1,
            opponent_type=ChessGame.OpponentType.STUDENT,
            opponent=self.student2,
            white_player=self.student1,
            status=ChessGame.Status.IN_PROGRESS,
            move_history=[],
            white_time=300,
            black_time=300,
            last_move_at=timezone.now()
        )
        self.client = APIClient()

    def test_valid_move(self):
        """Тест корректного хода."""
        self.client.force_authenticate(user=self.student1)
        url = reverse('chess-game-state', args=[self.game.id])
        data = {
            'from': 'e2',
            'to': 'e4',
            'promotion': 'q'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['game']['move_history']), 1)

    def test_wrong_turn_move(self):
        """Тест хода не в свой ход."""
        self.client.force_authenticate(user=self.student2)
        url = reverse('chess-game-state', args=[self.game.id])
        data = {
            'from': 'e7',
            'to': 'e5',
            'promotion': 'q'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что баланс не изменился
        self.student.refresh_from_db()
        self.assertEqual(self.student.balance, 100)


class TaskTests(APITestCase):
    """Тесты заданий."""

    def setUp(self):
        """Создание тестовых данных."""
        self.teacher = User.objects.create_user(
            username='test_teacher',
            password='testpass123',
            role='TEACHER'
        )
        self.student = User.objects.create_user(
            username='test_student',
            password='testpass123',
            role='STUDENT',
            student_group='FRONTEND',
            created_by=self.teacher
        )
        self.task = Task.objects.create(
            title='Тестовое задание',
            description='Описание задания',
            target_group='FRONTEND',
            reward_coins=50
        )

    def test_list_tasks_student(self):
        """Тест получения списка заданий студентом."""
        client = APIClient()
        client.force_authenticate(user=self.student)
        
        url = reverse('tasks-list')
        response = client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_tasks_wrong_group(self):
        """Тест: студент не видит задания другой группы."""
        self.student.student_group = 'BACKEND'
        self.student.save()
        
        client = APIClient()
        client.force_authenticate(user=self.student)
        
        url = reverse('tasks-list')
        response = client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class ProfileTests(APITestCase):
    """Тесты профиля."""

    def setUp(self):
        """Создание тестового пользователя."""
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123',
            role='STUDENT'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        """Тест получения профиля."""
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'test_user')

    def test_update_profile(self):
        """Тест обновления профиля."""
        url = reverse('profile')
        data = {
            'nickname': 'Новый никнейм'
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nickname'], 'Новый никнейм')
