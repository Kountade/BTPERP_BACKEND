# chantiers/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjetViewSet, PhaseViewSet, TacheViewSet,
    AffectationTacheViewSet, SousTraitantViewSet,
    InterventionSousTraitantViewSet, DocumentChantierViewSet,
    RapportQuotidienViewSet
)

router = DefaultRouter()
router.register('projets', ProjetViewSet, basename='projets')
router.register('phases', PhaseViewSet, basename='phases')
router.register('taches', TacheViewSet, basename='taches')
router.register('affectations', AffectationTacheViewSet, basename='affectations')
router.register('sous-traitants', SousTraitantViewSet, basename='sous-traitants')
router.register('interventions', InterventionSousTraitantViewSet, basename='interventions')
router.register('documents', DocumentChantierViewSet, basename='documents')
router.register('rapports', RapportQuotidienViewSet, basename='rapports')

urlpatterns = [
    path('', include(router.urls)),
]