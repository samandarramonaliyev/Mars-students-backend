"""
Права доступа для API Mars Devs.
"""
from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """Разрешение только для учителей."""
    message = 'Доступ только для преподавателей.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'TEACHER'
        )


class IsStudent(permissions.BasePermission):
    """Разрешение только для студентов."""
    message = 'Доступ только для студентов.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'STUDENT'
        )


class IsTeacherOrAdmin(permissions.BasePermission):
    """Разрешение для учителей и админов."""
    message = 'Доступ только для преподавателей и администраторов.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['TEACHER', 'ADMIN']
        )


class IsOwnerOrTeacher(permissions.BasePermission):
    """Разрешение для владельца объекта или учителя."""
    message = 'Доступ запрещён.'
    
    def has_object_permission(self, request, view, obj):
        # Учитель имеет доступ
        if request.user.role == 'TEACHER':
            return True
        # Владелец объекта имеет доступ
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'student'):
            return obj.student == request.user
        return obj == request.user
