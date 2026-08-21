# crm/urls.py
"""
URLs pour l'application CRM
API REST pour la gestion de la relation client
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClientViewSet,
    LeadViewSet,
    InteractionViewSet,
    AppelOffreViewSet,
)

# ✅ Création du routeur
router = DefaultRouter()

# ✅ Enregistrement des ViewSets
router.register('clients', ClientViewSet, basename='clients')
router.register('leads', LeadViewSet, basename='leads')
router.register('interactions', InteractionViewSet, basename='interactions')
router.register('appels-offres', AppelOffreViewSet, basename='appels-offres')

# ✅ Définition des urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]