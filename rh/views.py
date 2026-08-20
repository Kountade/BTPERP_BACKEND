    # rh/views.py - Ajouter FormationViewSet

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Sum, Q
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from .models import (
    Service, Poste, Employe, Contrat, Competence, EmployeCompetence,
    Formation, Pointage, HeureTravail, Absence, NoteDeFrais,
    PlanningEmploye, DPAE
)
from .serializers import (
    ServiceSerializer, ServiceCreateSerializer,
    PosteSerializer, PosteCreateSerializer,
    CompetenceSerializer,
    EmployeSerializer, EmployeDetailSerializer, EmployeCreateSerializer,
    ContratSerializer, ContratCreateSerializer,
    EmployeCompetenceSerializer,
    FormationSerializer,
    PointageSerializer, PointageCreateSerializer,
    HeureTravailSerializer,
    AbsenceSerializer, AbsenceCreateSerializer,
    NoteDeFraisSerializer, NoteDeFraisCreateSerializer,
    PlanningEmployeSerializer,
    DPAESerializer, DPAECreateSerializer,
)

User = get_user_model()



# ============================================================
# SERVICE VIEWSET
# ============================================================

class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet pour les services/départements"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Service.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceCreateSerializer
        return ServiceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif parent_id == 'null':
            queryset = queryset.filter(parent__isnull=True)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(code__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def employes(self, request, pk=None):
        service = self.get_object()
        employes = Employe.objects.filter(service=service)
        serializer = EmployeSerializer(employes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        service = self.get_object()
        employes = Employe.objects.filter(service=service)
        
        stats = {
            'total_employes': employes.count(),
            'par_poste': employes.values('poste__nom').annotate(
                count=Count('id')
            ),
            'par_contrat': Contrat.objects.filter(employe__service=service).values('situation').annotate(
                count=Count('id')
            ),
            'femmes': employes.filter(sexe='F').count(),
            'hommes': employes.filter(sexe='M').count(),
        }
        return Response(stats)


# ============================================================
# POSTE VIEWSET
# ============================================================

class PosteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les postes/métiers"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Poste.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PosteCreateSerializer
        return PosteSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        categorie = self.request.query_params.get('categorie')
        if categorie:
            queryset = queryset.filter(categorie=categorie)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(code__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def employes(self, request, pk=None):
        poste = self.get_object()
        employes = Employe.objects.filter(poste=poste)
        serializer = EmployeSerializer(employes, many=True)
        return Response(serializer.data)


# ============================================================
# COMPETENCE VIEWSET
# ============================================================

class CompetenceViewSet(viewsets.ModelViewSet):
    """ViewSet pour les compétences"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Competence.objects.all()
    serializer_class = CompetenceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'description', 'categorie']


# ============================================================
# CONTRAT VIEWSET
# ============================================================

class ContratViewSet(viewsets.ModelViewSet):
    """ViewSet pour les contrats"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Contrat.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ContratCreateSerializer
        return ContratSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        situation = self.request.query_params.get('situation')
        if situation:
            queryset = queryset.filter(situation=situation)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resilier(self, request, pk=None):
        """Résilie un contrat"""
        contrat = self.get_object()
        if contrat.statut == 'termine':
            return Response({"error": "Ce contrat est déjà terminé"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        contrat.statut = 'termine'
        contrat.save()
        return Response(ContratSerializer(contrat).data)
    
    @action(detail=True, methods=['post'])
    def suspendre(self, request, pk=None):
        """Suspend un contrat"""
        contrat = self.get_object()
        if contrat.statut == 'termine':
            return Response({"error": "Ce contrat est déjà terminé"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        contrat.statut = 'suspendu'
        contrat.save()
        return Response(ContratSerializer(contrat).data)
    
    @action(detail=True, methods=['post'])
    def reactiver(self, request, pk=None):
        """Réactive un contrat"""
        contrat = self.get_object()
        contrat.statut = 'actif'
        contrat.save()
        return Response(ContratSerializer(contrat).data)


# ============================================================
# EMPLOYE VIEWSET
# ============================================================

class EmployeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les employés"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Employe.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmployeCreateSerializer
        elif self.action == 'list':
            return EmployeSerializer
        return EmployeDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        service_id = self.request.query_params.get('service')
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        poste_id = self.request.query_params.get('poste')
        if poste_id:
            queryset = queryset.filter(poste_id=poste_id)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | 
                Q(prenom__icontains=search) | 
                Q(matricule__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques RH globales"""
        employes = Employe.objects.all()
        contrats = Contrat.objects.filter(statut='actif')
        
        stats = {
            'total_employes': employes.count(),
            'par_contrat': contrats.values('situation').annotate(
                count=Count('id')
            ),
            'par_service': employes.values('service__nom').annotate(
                count=Count('id')
            ),
            'par_poste': employes.values('poste__nom').annotate(
                count=Count('id')
            ),
            'sexe': {
                'hommes': employes.filter(sexe='M').count(),
                'femmes': employes.filter(sexe='F').count(),
            },
        }
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def contrats(self, request, pk=None):
        """Récupère les contrats d'un employé"""
        employe = self.get_object()
        contrats = employe.contrats.all()
        serializer = ContratSerializer(contrats, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_contrat(self, request, pk=None):
        """Ajoute un contrat à un employé"""
        employe = self.get_object()
        serializer = ContratCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employe=employe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def competences(self, request, pk=None):
        employe = self.get_object()
        competences = EmployeCompetence.objects.filter(employe=employe)
        serializer = EmployeCompetenceSerializer(competences, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_competence(self, request, pk=None):
        employe = self.get_object()
        serializer = EmployeCompetenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employe=employe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def formations(self, request, pk=None):
        employe = self.get_object()
        formations = employe.formations.all()
        serializer = FormationSerializer(formations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_formation(self, request, pk=None):
        employe = self.get_object()
        serializer = FormationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employe=employe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def pointages(self, request, pk=None):
        employe = self.get_object()
        pointages = employe.pointages.all()
        
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        if date_debut:
            pointages = pointages.filter(date__gte=date_debut)
        if date_fin:
            pointages = pointages.filter(date__lte=date_fin)
        
        pointages = pointages.order_by('-date', '-heure')
        serializer = PointageSerializer(pointages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def absences(self, request, pk=None):
        employe = self.get_object()
        absences = employe.absences.all()
        
        statut = request.query_params.get('statut')
        if statut:
            absences = absences.filter(statut=statut)
        
        absences = absences.order_by('-date_debut')
        serializer = AbsenceSerializer(absences, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def planning(self, request, pk=None):
        employe = self.get_object()
        planning = employe.plannings.all()
        
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        if date_debut:
            planning = planning.filter(date__gte=date_debut)
        if date_fin:
            planning = planning.filter(date__lte=date_fin)
        
        planning = planning.order_by('date', 'heure_debut')
        serializer = PlanningEmployeSerializer(planning, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def heures_travail(self, request, pk=None):
        employe = self.get_object()
        heures = employe.heures_travail.all()
        
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        if date_debut:
            heures = heures.filter(date__gte=date_debut)
        if date_fin:
            heures = heures.filter(date__lte=date_fin)
        
        heures = heures.order_by('-date')
        serializer = HeureTravailSerializer(heures, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes_frais(self, request, pk=None):
        employe = self.get_object()
        notes = employe.notes_frais.all()
        
        statut = request.query_params.get('statut')
        if statut:
            notes = notes.filter(statut=statut)
        
        notes = notes.order_by('-date_soumission')
        serializer = NoteDeFraisSerializer(notes, many=True)
        return Response(serializer.data)


# ============================================================
# POINTAGE VIEWSET
# ============================================================

class PointageViewSet(viewsets.ModelViewSet):
    """ViewSet pour les pointages"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pointage.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PointageCreateSerializer
        return PointageSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if date_debut:
            queryset = queryset.filter(date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date__lte=date_fin)
        
        projet_id = self.request.query_params.get('projet')
        if projet_id:
            queryset = queryset.filter(projet_id=projet_id)
        
        return queryset.order_by('-date', '-heure')


# ============================================================
# HEURE TRAVAIL VIEWSET
# ============================================================

class HeureTravailViewSet(viewsets.ModelViewSet):
    """ViewSet pour les heures travaillées"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = HeureTravail.objects.all()
    serializer_class = HeureTravailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if date_debut:
            queryset = queryset.filter(date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date__lte=date_fin)
        
        return queryset.order_by('-date')
    
    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        heure = self.get_object()
        heure.valide = True
        heure.valide_par = request.user
        heure.save()
        return Response(HeureTravailSerializer(heure).data)


# ============================================================
# ABSENCE VIEWSET
# ============================================================

class AbsenceViewSet(viewsets.ModelViewSet):
    """ViewSet pour les absences"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Absence.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AbsenceCreateSerializer
        return AbsenceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        type_absence = self.request.query_params.get('type')
        if type_absence:
            queryset = queryset.filter(type_absence=type_absence)
        
        return queryset.order_by('-date_debut')
    
    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        absence = self.get_object()
        serializer = AbsenceApproveSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['approuve']:
                absence.statut = 'approuvee'
            else:
                absence.statut = 'refusee'
            absence.approuve_par = request.user
            absence.save()
            return Response(AbsenceSerializer(absence).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        absence = self.get_object()
        if absence.statut in ['approuvee', 'refusee']:
            return Response(
                {"error": "Cette absence ne peut pas être annulée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        absence.statut = 'annulee'
        absence.save()
        return Response(AbsenceSerializer(absence).data)


# ============================================================
# NOTE DE FRAIS VIEWSET
# ============================================================

class NoteDeFraisViewSet(viewsets.ModelViewSet):
    """ViewSet pour les notes de frais"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = NoteDeFrais.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NoteDeFraisCreateSerializer
        return NoteDeFraisSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        return queryset.order_by('-date_soumission')
    
    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        note = self.get_object()
        serializer = NoteDeFraisApproveSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['approuve']:
                note.statut = 'approuvee'
                note.date_approbation = date.today()
            else:
                note.statut = 'refusee'
            note.approuve_par = request.user
            note.commentaire = serializer.validated_data.get('commentaire', '')
            note.save()
            return Response(NoteDeFraisSerializer(note).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def soumettre(self, request, pk=None):
        note = self.get_object()
        if note.statut != 'brouillon':
            return Response(
                {"error": "Cette note ne peut pas être soumise"},
                status=status.HTTP_400_BAD_REQUEST
            )
        note.statut = 'soumise'
        note.date_soumission = date.today()
        note.save()
        return Response(NoteDeFraisSerializer(note).data)


# ============================================================
# DPAE VIEWSET
# ============================================================
# rh/views.py - DPAEViewSet corrigé

class DPAEViewSet(viewsets.ModelViewSet):
    """ViewSet pour les DPAE"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = DPAE.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DPAECreateSerializer
        return DPAESerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        return queryset.order_by('-date_envoi')
    
    @action(detail=True, methods=['post'])
    def transmettre(self, request, pk=None):
        """Marque la DPAE comme transmise"""
        dpae = self.get_object()
        dpae.transmis = True
        dpae.save()
        return Response(DPAESerializer(dpae).data)
    
    @action(detail=False, methods=['post'])
    def generer_numero(self, request):
        """Génère un numéro de DPAE unique"""
        # ✅ Utiliser la méthode du modèle pour générer
        dpae = DPAE()
        new_num = dpae.generate_unique_number()
        return Response({"numero": new_num})

# ============================================================
# PLANNING EMPLOYE VIEWSET
# ============================================================

class PlanningEmployeViewSet(viewsets.ModelViewSet):
    """ViewSet pour le planning des employés"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = PlanningEmploye.objects.all()
    serializer_class = PlanningEmployeSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        contrat_id = self.request.query_params.get('contrat')
        if contrat_id:
            queryset = queryset.filter(contrat_id=contrat_id)
        
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        if date_debut:
            queryset = queryset.filter(date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date__lte=date_fin)
        
        return queryset.order_by('date', 'heure_debut')
    
    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        planning = self.get_object()
        planning.valide = True
        planning.save()
        return Response(PlanningEmployeSerializer(planning).data)




# ============================================================
# FORMATION VIEWSET - À AJOUTER
# ============================================================

class FormationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les formations"""
    
    permission_classes = [permissions.IsAuthenticated]
    queryset = Formation.objects.all()
    serializer_class = FormationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrer par employé
        employe_id = self.request.query_params.get('employe')
        if employe_id:
            queryset = queryset.filter(employe_id=employe_id)
        
        # Filtrer par validation
        valide = self.request.query_params.get('valide')
        if valide is not None:
            queryset = queryset.filter(valide=valide.lower() == 'true')
        
        # Recherche
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(organisme__icontains=search) |
                Q(employe__nom__icontains=search) |
                Q(employe__prenom__icontains=search)
            )
        
        return queryset.order_by('-date_debut')
    
    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """Valide une formation"""
        formation = self.get_object()
        formation.valide = True
        formation.save()
        return Response(FormationSerializer(formation).data)
    
    @action(detail=True, methods=['post'])
    def invalider(self, request, pk=None):
        """Invalide une formation"""
        formation = self.get_object()
        formation.valide = False
        formation.save()
        return Response(FormationSerializer(formation).data)