# rh/urls.py
"""
URLs pour l'application RH
API REST pour la gestion des ressources humaines
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ✅ IMPORTS CORRECTS DES VIEWSETS
from .views import (
    ServiceViewSet,
    PosteViewSet,
    CompetenceViewSet,
    EmployeViewSet,
    PointageViewSet,
    HeureTravailViewSet,
    AbsenceViewSet,
    NoteDeFraisViewSet,
    PlanningEmployeViewSet,
    DPAEViewSet
)

# ✅ Création du routeur
router = DefaultRouter()

# ✅ Enregistrement des ViewSets
router.register('services', ServiceViewSet, basename='services')
router.register('postes', PosteViewSet, basename='postes')
router.register('employes', EmployeViewSet, basename='employes')
router.register('competences', CompetenceViewSet, basename='competences')
router.register('pointages', PointageViewSet, basename='pointages')
router.register('heures-travail', HeureTravailViewSet, basename='heures-travail')
router.register('absences', AbsenceViewSet, basename='absences')
router.register('notes-frais', NoteDeFraisViewSet, basename='notes-frais')
router.register('planning', PlanningEmployeViewSet, basename='planning')
router.register('dpae', DPAEViewSet, basename='dpae')

# ✅ Définition des urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]