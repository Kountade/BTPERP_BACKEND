# chantiers/views.py

from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Sum, Q, Avg
from django.db.models.functions import TruncMonth
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

from .models import (
    Projet, Phase, Tache, AffectationTache,
    SousTraitant, InterventionSousTraitant,
    DocumentChantier, RapportQuotidien
)
from .serializers import (
    ProjetSerializer,
    ProjetDetailSerializer,
    ProjetCreateSerializer,
    PhaseSerializer,
    PhaseCreateSerializer,
    TacheSerializer,
    TacheDetailSerializer,
    TacheCreateSerializer,
    AffectationTacheSerializer,
    AffectationTacheCreateSerializer,
    SousTraitantSerializer,
    SousTraitantCreateSerializer,
    InterventionSousTraitantSerializer,
    InterventionSousTraitantCreateSerializer,
    DocumentChantierSerializer,
    DocumentChantierCreateSerializer,
    RapportQuotidienSerializer,
    RapportQuotidienCreateSerializer,
)

User = get_user_model()


# ============================================================
# PERMISSION PERSONNALISÉE
# ============================================================

class HasAgenceAccess(permissions.BasePermission):
    """
    Permission pour vérifier l'accès à l'agence.
    - PDG a accès à tout
    - Les autres utilisateurs n'ont accès qu'à leurs agences.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

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
        if hasattr(obj, 'projet') and obj.projet and obj.projet.agence:
            return request.user.peut_acceder_agence(obj.projet.agence.id)
        if hasattr(obj, 'phase') and obj.phase and obj.phase.projet and obj.phase.projet.agence:
            return request.user.peut_acceder_agence(obj.phase.projet.agence.id)
        if hasattr(obj, 'interventions') and obj.interventions.exists():
            for inter in obj.interventions.all():
                if inter.projet and inter.projet.agence and request.user.peut_acceder_agence(inter.projet.agence.id):
                    return True
        return False


# ============================================================
# PROJET VIEWSET
# ============================================================

class ProjetViewSet(viewsets.ModelViewSet):
    """ViewSet pour les projets/chantiers - Multi-agences"""
    
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Projet.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'nom', 'ville', 'client__nom']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjetCreateSerializer
        elif self.action == 'list':
            return ProjetSerializer
        return ProjetDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(agence_id__in=agences_ids)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        type_projet = self.request.query_params.get('type')
        if type_projet:
            queryset = queryset.filter(type_projet=type_projet)
        
        client_id = self.request.query_params.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        chef_projet_id = self.request.query_params.get('chef_projet')
        if chef_projet_id:
            queryset = queryset.filter(chef_projet_id=chef_projet_id)
        
        actif = self.request.query_params.get('actif')
        if actif and actif.lower() == 'true':
            queryset = queryset.exclude(statut__in=['termine', 'livre'])
        
        en_retard = self.request.query_params.get('en_retard')
        if en_retard and en_retard.lower() == 'true':
            queryset = queryset.filter(
                Q(statut__in=['etude', 'encours', 'suspendu']),
                date_fin_previsionnelle__lt=date.today()
            )
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(nom__icontains=search) |
                Q(ville__icontains=search) |
                Q(client__nom__icontains=search)
            )
        
        return queryset.order_by('-date_debut')
    
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
    def phases(self, request, pk=None):
        projet = self.get_object()
        phases = projet.phases.all()
        serializer = PhaseSerializer(phases, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def taches(self, request, pk=None):
        projet = self.get_object()
        taches = Tache.objects.filter(phase__projet=projet)
        serializer = TacheSerializer(taches, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def interventions(self, request, pk=None):
        projet = self.get_object()
        interventions = projet.interventions_st.all()
        serializer = InterventionSousTraitantSerializer(interventions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        projet = self.get_object()
        docs = projet.documents.all()
        serializer = DocumentChantierSerializer(docs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def rapports(self, request, pk=None):
        projet = self.get_object()
        rapports = projet.rapports_quotidiens.all()
        serializer = RapportQuotidienSerializer(rapports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        stats = {
            'total_projets': queryset.count(),
            'par_statut': queryset.values('statut').annotate(count=Count('id')),
            'par_type': queryset.values('type_projet').annotate(count=Count('id')),
            'budget_total': queryset.aggregate(total=Sum('budget_total'))['total'] or 0,
            'cout_total': queryset.aggregate(
                total=Sum('cout_reel_mo') + Sum('cout_reel_materiaux') + Sum('cout_reel_sous_traitance') + Sum('cout_reel_frais_generaux')
            )['total'] or 0,
            'taux_avancement_moyen': queryset.aggregate(moyenne=Avg('taux_avancement'))['moyenne'] or 0,
            'projets_retard': queryset.filter(
                Q(statut__in=['etude', 'encours', 'suspendu']),
                date_fin_previsionnelle__lt=date.today()
            ).count(),
            'projets_termines': queryset.filter(statut__in=['termine', 'livre']).count(),
        }
        return Response(stats)

    @action(detail=True, methods=['get'], url_path='pdf')
    def generer_pdf(self, request, pk=None):
        """Génère un PDF récapitulatif du projet"""
        projet = self.get_object()
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Titre
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height - 2*cm, f"PROJET : {projet.code} - {projet.nom}")
        c.line(2*cm, height - 2.5*cm, width - 2*cm, height - 2.5*cm)
        
        # Infos générales
        c.setFont("Helvetica", 11)
        y = height - 4*cm
        infos = [
            f"Client : {projet.client.nom}",
            f"Type : {projet.get_type_projet_display()}",
            f"Statut : {projet.get_statut_display()}",
            f"Date début : {projet.date_debut.strftime('%d/%m/%Y')}",
            f"Date fin prévue : {projet.date_fin_previsionnelle.strftime('%d/%m/%Y')}",
            f"Date fin réelle : {projet.date_fin_reelle.strftime('%d/%m/%Y') if projet.date_fin_reelle else 'Non terminé'}",
            f"Budget total : {projet.budget_total:,.2f} €",
            f"Taux d'avancement : {projet.taux_avancement}%",
            f"Adresse : {projet.adresse_chantier}, {projet.code_postal} {projet.ville}",
        ]
        for info in infos:
            c.drawString(2*cm, y, info)
            y -= 0.7*cm
        
        # Détails budgétaires
        y -= 0.5*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y, "Détails budgétaires")
        y -= 0.7*cm
        c.setFont("Helvetica", 11)
        budgets = [
            f"Main d'œuvre : {projet.budget_mo:,.2f} € (réel : {projet.cout_reel_mo:,.2f} €)",
            f"Matériaux : {projet.budget_materiaux:,.2f} € (réel : {projet.cout_reel_materiaux:,.2f} €)",
            f"Sous-traitance : {projet.budget_sous_traitance:,.2f} € (réel : {projet.cout_reel_sous_traitance:,.2f} €)",
            f"Frais généraux : {projet.budget_frais_generaux:,.2f} € (réel : {projet.cout_reel_frais_generaux:,.2f} €)",
        ]
        for b in budgets:
            c.drawString(2*cm, y, b)
            y -= 0.5*cm
        
        # Phases
        y -= 0.5*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y, "Phases du projet")
        y -= 0.7*cm
        c.setFont("Helvetica", 10)
        for phase in projet.phases.all():
            if y < 2*cm:
                c.showPage()
                y = height - 2*cm
                c.setFont("Helvetica", 10)
            c.drawString(2.5*cm, y, f"- {phase.nom} ({phase.get_type_phase_display()})")
            y -= 0.4*cm
            c.drawString(3*cm, y, f"  Avancement : {phase.taux_avancement}% - Budget : {phase.budget:,.2f} € - Réel : {phase.cout_reel:,.2f} €")
            y -= 0.5*cm
        
        # Pied de page
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(2*cm, 1.5*cm, f"Document généré le {date.today().strftime('%d/%m/%Y')} - BTP ERP")
        
        c.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="projet_{projet.code}.pdf"'
        return response


# ============================================================
# PHASE VIEWSET
# ============================================================

class PhaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Phase.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PhaseCreateSerializer
        return PhaseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(projet__agence_id__in=agences_ids)
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(projet_id=projet_id)
        return queryset.order_by('ordre')
    
    def perform_create(self, serializer):
        serializer.save()


# ============================================================
# TÂCHE VIEWSET
# ============================================================

class TacheViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = Tache.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'description']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TacheCreateSerializer
        elif self.action == 'retrieve':
            return TacheDetailSerializer
        return TacheSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(phase__projet__agence_id__in=agences_ids)
        phase_id = self.request.query_params.get('phase')
        if phase_id:
            queryset = queryset.filter(phase_id=phase_id)
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(phase__projet_id=projet_id)
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        priorite = self.request.query_params.get('priorite')
        if priorite:
            queryset = queryset.filter(priorite=priorite)
        responsable_id = self.request.query_params.get('responsable')
        if responsable_id:
            queryset = queryset.filter(responsable_id=responsable_id)
        return queryset.order_by('-priorite', 'date_fin_previsionnelle')
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def affecter_employe(self, request, pk=None):
        tache = self.get_object()
        serializer = AffectationTacheCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tache=tache)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def changer_statut(self, request, pk=None):
        tache = self.get_object()
        new_statut = request.data.get('statut')
        if new_statut not in dict(Tache.STATUT_CHOICES):
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)
        tache.statut = new_statut
        if new_statut == 'terminee':
            tache.date_fin_reelle = date.today()
        tache.save()
        return Response(TacheSerializer(tache).data)


# ============================================================
# AFFECTATION TÂCHE VIEWSET
# ============================================================

class AffectationTacheViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = AffectationTache.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AffectationTacheCreateSerializer
        return AffectationTacheSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(tache__phase__projet__agence_id__in=agences_ids)
        tache_id = self.request.query_params.get('tache')
        if tache_id:
            queryset = queryset.filter(tache_id=tache_id)
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        return queryset


# ============================================================
# SOUS-TRAITANT VIEWSET
# ============================================================

class SousTraitantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = SousTraitant.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'siret', 'ville']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SousTraitantCreateSerializer
        return SousTraitantSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(interventions__projet__agence_id__in=agences_ids).distinct()
        actif = self.request.query_params.get('actif')
        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(siret__icontains=search) |
                Q(ville__icontains=search)
            )
        return queryset.order_by('nom')


# ============================================================
# INTERVENTION SOUS-TRAITANT VIEWSET
# ============================================================

class InterventionSousTraitantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = InterventionSousTraitant.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InterventionSousTraitantCreateSerializer
        return InterventionSousTraitantSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(projet__agence_id__in=agences_ids)
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(projet_id=projet_id)
        sous_traitant_id = self.request.query_params.get('sous_traitant')
        if sous_traitant_id:
            queryset = queryset.filter(sous_traitant_id=sous_traitant_id)
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset.order_by('-date_debut')


# ============================================================
# DOCUMENT CHANTIER VIEWSET
# ============================================================

class DocumentChantierViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = DocumentChantier.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'description']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentChantierCreateSerializer
        return DocumentChantierSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(projet__agence_id__in=agences_ids)
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(projet_id=projet_id)
        type_doc = self.request.query_params.get('type')
        if type_doc:
            queryset = queryset.filter(type_document=type_doc)
        return queryset.order_by('-date_upload')
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(auteur=user)


# ============================================================
# RAPPORT QUOTIDIEN VIEWSET
# ============================================================

class RapportQuotidienViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasAgenceAccess]
    queryset = RapportQuotidien.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RapportQuotidienCreateSerializer
        return RapportQuotidienSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.est_pdg():
            agences_ids = user.get_agences().values_list('id', flat=True)
            queryset = queryset.filter(projet__agence_id__in=agences_ids)
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(projet_id=projet_id)
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if date_debut:
            queryset = queryset.filter(date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date__lte=date_fin)
        return queryset.order_by('-date')
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(redacteur=user)