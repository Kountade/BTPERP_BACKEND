# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterViewset,
    LoginViewset,
    UserViewset,
    ProfileViewset,
    AgenceViewset,
    RoleAgenceViewset,
    AgencesPubliquesViewset
)

router = DefaultRouter()
router.register('register', RegisterViewset, basename='register')
router.register('login', LoginViewset, basename='login')
router.register('users', UserViewset, basename='users')
router.register('profile', ProfileViewset, basename='profile')
router.register('agences', AgenceViewset, basename='agences')
router.register('roles', RoleAgenceViewset, basename='roles')
router.register('agences-publiques', AgencesPubliquesViewset, basename='agences-publiques')

urlpatterns = [
    path('', include(router.urls)),
]