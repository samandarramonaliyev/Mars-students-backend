"""
URL маршруты для API Mars Devs.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView, ProfileView,
    StudentListCreateView, StudentDetailView, StudentCoinsView,
    TaskListView, TaskSubmitView,
    TaskSubmissionsListView, TaskSubmissionReviewView, MySubmissionsView,
    MyCoinTransactionsView, TypingResultsView,
    ChessHistoryView, CourseListView, TeacherStatsView,
    # Шахматы (реальная игра)
    ChessStartGameView, ChessFinishGameView, ChessMyGamesView,
    ChessOnlineStudentsView, ChessInviteView, ChessMyInvitesView,
    ChessRespondInviteView, ChessGameStateView, ChessCancelInviteView,
    CoinNotificationsView, CoinNotificationsMarkSeenView,
    # Магазин
    ShopProductsView, ShopBuyView, ShopPurchaseHistoryView
)

urlpatterns = [
    # Аутентификация
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Профиль
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Студенты (для учителей)
    path('students/', StudentListCreateView.as_view(), name='students-list-create'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='student-detail'),
    path('students/<int:pk>/coins/', StudentCoinsView.as_view(), name='student-coins'),
    
    # Задания
    path('tasks/', TaskListView.as_view(), name='tasks-list'),
    path('tasks/<int:task_id>/submit/', TaskSubmitView.as_view(), name='task-submit'),
    
    # Отправки заданий
    path('submissions/', TaskSubmissionsListView.as_view(), name='submissions-list'),
    path('submissions/<int:submission_id>/review/', TaskSubmissionReviewView.as_view(), name='submission-review'),
    path('my-submissions/', MySubmissionsView.as_view(), name='my-submissions'),
    
    # Монеты
    path('my-coins/', MyCoinTransactionsView.as_view(), name='my-coins'),
    
    # Тест печати
    path('typing-results/', TypingResultsView.as_view(), name='typing-results'),
    
    # Шахматы (записи учителя)
    path('chess-history/', ChessHistoryView.as_view(), name='chess-history'),
    
    # Шахматы (реальная игра)
    path('chess/start/', ChessStartGameView.as_view(), name='chess-start'),
    path('chess/finish/', ChessFinishGameView.as_view(), name='chess-finish'),
    path('chess/my-games/', ChessMyGamesView.as_view(), name='chess-my-games'),
    path('chess/online-students/', ChessOnlineStudentsView.as_view(), name='chess-online-students'),
    path('chess/invite/', ChessInviteView.as_view(), name='chess-invite'),
    path('chess/my-invites/', ChessMyInvitesView.as_view(), name='chess-my-invites'),
    path('chess/respond-invite/', ChessRespondInviteView.as_view(), name='chess-respond-invite'),
    path('chess/cancel-invite/', ChessCancelInviteView.as_view(), name='chess-cancel-invite'),
    path('chess/game/<int:game_id>/', ChessGameStateView.as_view(), name='chess-game-state'),
    
    # Уведомления о coin
    path('notifications/coins/', CoinNotificationsView.as_view(), name='coin-notifications'),
    path('notifications/coins/mark-seen/', CoinNotificationsMarkSeenView.as_view(), name='coin-notifications-mark-seen'),
    
    # Курсы
    path('courses/', CourseListView.as_view(), name='courses-list'),
    
    # Статистика учителя
    path('teacher/stats/', TeacherStatsView.as_view(), name='teacher-stats'),
    
    # Магазин
    path('shop/products/', ShopProductsView.as_view(), name='shop-products'),
    path('shop/buy/', ShopBuyView.as_view(), name='shop-buy'),
    path('shop/purchases/', ShopPurchaseHistoryView.as_view(), name='shop-purchases'),
]
