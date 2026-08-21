# crm/views.py
"""
Vues pour l'application CRM - Multi-agences
API REST pour la gestion de la relation client
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from .models import Client, Lead, Interaction, AppelOffre
from .serializers import *

User = get_user_model()


# ============================================================
# PERMISSION PERSONNALISÉE
# ============================================================

class HasAgenceAccess(permissions.BasePermission):
    """
    Permission pour vérifier que l'utilisateur a accès à l'agence
    - PDG a accès à tout
    - Les autres utilisateurs n'ont accès qu'à leurs agences
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        # Vérifier si l'utilisateur a des agences
        return request.user.get_agences().exists()

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        # Vérifier que l'objet appartient à une agence de l'utilisateur
        if hasattr(obj, 'agence') and obj.agence:
            return request.user.peut_acceder_agence(obj.agence.id)

        return False


# ============================================================
# CLIENT VIEWSET
# ============================================================

class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet pour les clients - Multi-agences"""
    
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Client.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'email', 'siret', 'ville']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        elif self.action == 'list':
            return ClientSerializer
        return ClientDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # ✅ FILTRER PAR AGENCE
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(agence_id__in=agences_ids)
        
        # Filtrer par type
        type_client = self.request.query_params.get('type')
        if type_client:
            queryset = queryset.filter(type_client=type_client)
        
        # Filtrer par actif
        actif = self.request.query_params.get('actif')
        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')
        
        # Recherche
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(email__icontains=search) |
                Q(ville__icontains=search)
            )
        
        return queryset.order_by('nom')
    
    def perform_create(self, serializer):
        user = self.request.user
        agence_id = self.request.data.get('agence')
        
        if not agence_id:
            agence = user.get_agence_principale()
            if agence:
                serializer.save(created_by=user, agence=agence)
                return
        
        serializer.save(created_by=user)
    
    @action(detail=True, methods=['get'])
    def leads(self, request, pk=None):
        client = self.get_object()
        leads = client.leads.all()
        serializer = LeadSerializer(leads, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def appels_offres(self, request, pk=None):
        client = self.get_object()
        appels = client.appels_offres.all()
        serializer = AppelOffreSerializer(appels, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def interactions(self, request, pk=None):
        client = self.get_object()
        interactions = client.interactions.all()
        serializer = InteractionSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques des clients"""
        user = self.request.user
        clients = self.get_queryset()
        
        stats = {
            'total': clients.count(),
            'actifs': clients.filter(actif=True).count(),
            'inactifs': clients.filter(actif=False).count(),
            'par_type': clients.values('type_client').annotate(
                count=Count('id')
            ),
            'note_moyenne': clients.aggregate(
                moyenne=Sum('note') / clients.count() if clients.count() > 0 else 0
            )['moyenne'] or 0,
        }
        return Response(stats)


# ============================================================
# LEAD VIEWSET
# ============================================================

class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet pour les leads/prospects - Multi-agences"""
    
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Lead.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'email', 'societe']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LeadCreateSerializer
        elif self.action == 'list':
            return LeadSerializer
        return LeadDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # ✅ FILTRER PAR AGENCE
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(agence_id__in=agences_ids)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        commercial_id = self.request.query_params.get('commercial')
        if commercial_id:
            queryset = queryset.filter(commercial_id=commercial_id)
        
        recent = self.request.query_params.get('recent')
        if recent and recent.lower() == 'true':
            date_limit = date.today() - timedelta(days=30)
            queryset = queryset.filter(created_at__date__gte=date_limit)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(email__icontains=search) |
                Q(societe__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        user = self.request.user
        agence_id = self.request.data.get('agence')
        
        if not agence_id:
            agence = user.get_agence_principale()
            if agence:
                serializer.save(commercial=user, agence=agence)
                return
        
        if not serializer.validated_data.get('commercial'):
            serializer.save(commercial=user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def changer_statut(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadChangeStatutSerializer(data=request.data)
        
        if serializer.is_valid():
            new_statut = serializer.validated_data['statut']
            lead.statut = new_statut
            
            if new_statut == 'perdu':
                lead.date_perte = date.today()
                lead.motif_perte = serializer.validated_data.get('motif_perte', '')
            
            lead.save()
            return Response(LeadSerializer(lead).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def convertir_client(self, request, pk=None):
        lead = self.get_object()
        
        if lead.statut == 'gagne':
            # ✅ Récupérer l'agence du lead
            agence = lead.agence
            
            client_data = {
                'nom': lead.societe or lead.nom,
                'email': lead.email,
                'telephone': lead.telephone,
                'type_client': 'particulier',
                'contact_principal': lead.nom,
                'contact_telephone': lead.telephone,
                'contact_email': lead.email,
                'agence': agence,
                'created_by': self.request.user,
            }
            
            existing_client = Client.objects.filter(agence=agence, email=lead.email).first()
            if existing_client:
                lead.client = existing_client
                lead.save()
                return Response({
                    'message': 'Lead déjà associé à un client existant',
                    'client': ClientSerializer(existing_client).data
                })
            
            client = Client.objects.create(**client_data)
            lead.client = client
            lead.save()
            
            return Response({
                'message': 'Lead converti en client avec succès',
                'client': ClientSerializer(client).data
            })
        
        return Response({
            'error': 'Seul un lead avec le statut "Gagné" peut être converti en client'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def interactions(self, request, pk=None):
        lead = self.get_object()
        interactions = lead.interactions.all()
        serializer = InteractionSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques des leads"""
        leads = self.get_queryset()
        
        stats = {
            'total': leads.count(),
            'par_statut': leads.values('statut').annotate(
                count=Count('id')
            ),
            'par_source': leads.values('source').annotate(
                count=Count('id')
            ),
            'par_commercial': leads.values('commercial__username').annotate(
                count=Count('id')
            ),
            'taux_conversion': {
                'gagnes': leads.filter(statut='gagne').count(),
                'perdus': leads.filter(statut='perdu').count(),
                'en_cours': leads.filter(statut__in=['nouveau', 'contacte', 'qualifie', 'devis']).count(),
            }
        }
        return Response(stats)


# ============================================================
# INTERACTION VIEWSET
# ============================================================

class InteractionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les interactions - Multi-agences"""
    
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Interaction.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InteractionCreateSerializer
        return InteractionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # ✅ FILTRER PAR AGENCE
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(agence_id__in=agences_ids)
        
        lead_id = self.request.query_params.get('lead')
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        
        client_id = self.request.query_params.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        type_interaction = self.request.query_params.get('type')
        if type_interaction:
            queryset = queryset.filter(type_interaction=type_interaction)
        
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if date_debut:
            queryset = queryset.filter(date__date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date__date__lte=date_fin)
        
        return queryset.order_by('-date')
    
    def perform_create(self, serializer):
        user = self.request.user
        agence_id = self.request.data.get('agence')
        
        if not agence_id:
            agence = user.get_agence_principale()
            if agence:
                serializer.save(responsable=user, agence=agence)
                return
        
        if not serializer.validated_data.get('responsable'):
            serializer.save(responsable=user)
        else:
            serializer.save()


# ============================================================
# APPEL D'OFFRES VIEWSET
# ============================================================

class AppelOffreViewSet(viewsets.ModelViewSet):
    """ViewSet pour les appels d'offres - Multi-agences"""
    
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = AppelOffre.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['reference', 'objet', 'client__nom']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AppelOffreCreateSerializer
        return AppelOffreSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # ✅ FILTRER PAR AGENCE
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(agence_id__in=agences_ids)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        client_id = self.request.query_params.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        responsable_id = self.request.query_params.get('responsable')
        if responsable_id:
            queryset = queryset.filter(responsable_id=responsable_id)
        
        en_retard = self.request.query_params.get('en_retard')
        if en_retard and en_retard.lower() == 'true':
            queryset = queryset.filter(
                Q(statut__in=['recu', 'en_cours']),
                date_limite__lt=date.today()
            )
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(objet__icontains=search) |
                Q(client__nom__icontains=search)
            )
        
        return queryset.order_by('-date_limite')
    
    def perform_create(self, serializer):
        user = self.request.user
        agence_id = self.request.data.get('agence')
        
        if not agence_id:
            agence = user.get_agence_principale()
            if agence:
                serializer.save(responsable=user, agence=agence)
                return
        
        if not serializer.validated_data.get('responsable'):
            serializer.save(responsable=user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def changer_statut(self, request, pk=None):
        appel = self.get_object()
        serializer = AppelOffreChangeStatutSerializer(data=request.data)
        
        if serializer.is_valid():
            new_statut = serializer.validated_data['statut']
            appel.statut = new_statut
            
            if new_statut in ['soumis', 'gagne']:
                appel.date_soumission = date.today()
            
            if new_statut == 'gagne' and serializer.validated_data.get('montant_soumis'):
                appel.montant_soumis = serializer.validated_data['montant_soumis']
            
            appel.save()
            return Response(AppelOffreSerializer(appel).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques des appels d'offres"""
        appels = self.get_queryset()
        
        stats = {
            'total': appels.count(),
            'par_statut': appels.values('statut').annotate(
                count=Count('id')
            ),
            'valeur_totale': appels.aggregate(
                total=Sum('budget_estime')
            )['total'] or 0,
            'valeur_gagnee': appels.filter(statut='gagne').aggregate(
                total=Sum('montant_soumis')
            )['total'] or 0,
            'taux_succes': {
                'gagnes': appels.filter(statut='gagne').count(),
                'perdus': appels.filter(statut='perdu').count(),
                'en_cours': appels.filter(statut__in=['recu', 'en_cours', 'soumis']).count(),
            }
        }
        return Response(stats)