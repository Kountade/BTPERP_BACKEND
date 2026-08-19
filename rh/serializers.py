# rh/serializers.py
"""
Serializers pour l'application RH
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from .models import (
    Service, Poste, Employe, Competence, EmployeCompetence,
    Formation, Pointage, HeureTravail, Absence, NoteDeFrais,
    PlanningEmploye, DPAE
)

User = get_user_model()


# ============================================================
# SERVICE SERIALIZER
# ============================================================

class ServiceSerializer(serializers.ModelSerializer):
    """Serializer pour les services/départements"""
    
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    nb_employes = serializers.SerializerMethodField()
    sous_services = serializers.SerializerMethodField()
    parent_nom = serializers.CharField(source='parent.nom', read_only=True, default=None)
    
    class Meta:
        model = Service
        fields = ('id', 'nom', 'code', 'responsable', 'responsable_nom', 
                  'parent', 'parent_nom', 'nb_employes', 'sous_services')
        read_only_fields = ('id',)
    
    def get_nb_employes(self, obj):
        return Employe.objects.filter(service=obj, actif=True).count()
    
    def get_sous_services(self, obj):
        sous_services = Service.objects.filter(parent=obj)
        return ServiceSerializer(sous_services, many=True).data


class ServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'nom', 'code', 'responsable', 'parent')
    
    def validate_code(self, value):
        if Service.objects.filter(code=value).exists():
            raise serializers.ValidationError("Ce code de service existe déjà")
        return value


# ============================================================
# POSTE SERIALIZER
# ============================================================

class PosteSerializer(serializers.ModelSerializer):
    categorie_display = serializers.CharField(source='get_categorie_display', read_only=True)
    nb_employes = serializers.SerializerMethodField()
    competences_requises_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Poste
        fields = ('id', 'nom', 'description', 'code', 'categorie', 'categorie_display',
                  'niveau', 'coefficient', 'competences_requises', 'competences_requises_detail',
                  'nb_employes')
        read_only_fields = ('id',)
    
    def get_nb_employes(self, obj):
        return Employe.objects.filter(poste=obj, actif=True).count()
    
    def get_competences_requises_detail(self, obj):
        competences = obj.competences_requises.all()
        return CompetenceSerializer(competences, many=True).data


class PosteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poste
        fields = ('id', 'nom', 'description', 'code', 'categorie', 'niveau', 
                  'coefficient', 'competences_requises')
    
    def validate_code(self, value):
        if Poste.objects.filter(code=value).exists():
            raise serializers.ValidationError("Ce code de poste existe déjà")
        return value


# ============================================================
# COMPETENCE SERIALIZER
# ============================================================

class CompetenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competence
        fields = ('id', 'nom', 'description', 'categorie')
        read_only_fields = ('id',)


# ============================================================
# EMPLOYE SERIALIZER - CORRIGÉ
# ============================================================

class EmployeSerializer(serializers.ModelSerializer):
    """Serializer de base pour les employés"""
    
    # ✅ CORRECTION : Utiliser une méthode personnalisée au lieu de get_full_name
    full_name = serializers.SerializerMethodField()
    age = serializers.IntegerField(read_only=True)
    anciennete = serializers.IntegerField(read_only=True)
    service_nom = serializers.CharField(source='service.nom', read_only=True, default=None)
    poste_nom = serializers.CharField(source='poste.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    situation_display = serializers.CharField(source='get_situation_display', read_only=True)
    
    class Meta:
        model = Employe
        fields = ('id', 'matricule', 'nom', 'prenom', 'full_name', 'sexe', 
                  'date_naissance', 'age', 'lieu_naissance', 'nationalite',
                  'email', 'telephone', 'adresse', 'code_postal', 'ville',
                  'situation', 'situation_display', 'poste', 'poste_nom',
                  'service', 'service_nom', 'date_embauche', 'anciennete',
                  'date_fin_contrat', 'date_essai_fin', 'salaire_base',
                  'taux_horaire', 'prime_panier', 'indemnite_km', 'prime_anciennete',
                  'actif', 'disponible', 'numero_securite_sociale', 'num_permis',
                  'permis_valide', 'agence', 'agence_nom', 'user')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    # ✅ CORRECTION : Méthode personnalisée pour le nom complet
    def get_full_name(self, obj):
        return f"{obj.prenom or ''} {obj.nom or ''}".strip() or obj.email or 'Employé'


class EmployeDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les employés"""
    
    # ✅ CORRECTION : Utiliser une méthode personnalisée
    full_name = serializers.SerializerMethodField()
    age = serializers.IntegerField(read_only=True)
    anciennete = serializers.IntegerField(read_only=True)
    service_nom = serializers.CharField(source='service.nom', read_only=True, default=None)
    poste_nom = serializers.CharField(source='poste.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    situation_display = serializers.CharField(source='get_situation_display', read_only=True)
    
    # Relations
    competences = serializers.SerializerMethodField()
    formations = serializers.SerializerMethodField()
    pointages_recents = serializers.SerializerMethodField()
    absences_en_cours = serializers.SerializerMethodField()
    heures_mois = serializers.SerializerMethodField()
    
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    
    class Meta:
        model = Employe
        fields = ('id', 'matricule', 'nom', 'prenom', 'full_name', 'sexe', 
                  'date_naissance', 'age', 'lieu_naissance', 'nationalite',
                  'email', 'telephone', 'adresse', 'code_postal', 'ville',
                  'situation', 'situation_display', 'poste', 'poste_nom',
                  'service', 'service_nom', 'date_embauche', 'anciennete',
                  'date_fin_contrat', 'date_essai_fin', 'salaire_base',
                  'taux_horaire', 'prime_panier', 'indemnite_km', 'prime_anciennete',
                  'actif', 'disponible', 'numero_securite_sociale', 'num_permis',
                  'permis_valide', 'agence', 'agence_nom', 'user', 'user_email',
                  'user_username', 'competences', 'formations', 'pointages_recents', 
                  'absences_en_cours', 'heures_mois')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    # ✅ CORRECTION : Méthode personnalisée
    def get_full_name(self, obj):
        return f"{obj.prenom or ''} {obj.nom or ''}".strip() or obj.email or 'Employé'
    
    def get_competences(self, obj):
        employe_comp = obj.competences.filter(employe=obj)
        return EmployeCompetenceSerializer(employe_comp, many=True).data
    
    def get_formations(self, obj):
        formations = obj.formations.all()
        return FormationSerializer(formations, many=True).data
    
    def get_pointages_recents(self, obj):
        pointages = obj.pointages.order_by('-date', '-heure')[:10]
        return PointageSerializer(pointages, many=True).data
    
    def get_absences_en_cours(self, obj):
        today = date.today()
        absences = obj.absences.filter(
            Q(statut__in=['demandee', 'approuvee']),
            Q(date_debut__lte=today, date_fin__gte=today) | Q(date_debut__gte=today)
        )
        return AbsenceSerializer(absences, many=True).data
    
    def get_heures_mois(self, obj):
        today = date.today()
        debut_mois = today.replace(day=1)
        heures = obj.heures_travail.filter(
            date__gte=debut_mois,
            date__lte=today
        ).aggregate(
            total_normales=Sum('heures_normales'),
            total_supplementaires=Sum('heures_supplementaires'),
            total_nuit=Sum('heures_nuit'),
            total_weekend=Sum('heures_weekend')
        )
        return {
            'heures_normales': float(heures.get('total_normales') or 0),
            'heures_supplementaires': float(heures.get('total_supplementaires') or 0),
            'heures_nuit': float(heures.get('total_nuit') or 0),
            'heures_weekend': float(heures.get('total_weekend') or 0)
        }


class EmployeCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Employe
        fields = ('id', 'matricule', 'nom', 'prenom', 'sexe', 'date_naissance',
                  'lieu_naissance', 'nationalite', 'email', 'telephone',
                  'adresse', 'code_postal', 'ville', 'situation', 'poste',
                  'service', 'date_embauche', 'date_fin_contrat', 'date_essai_fin',
                  'salaire_base', 'taux_horaire', 'prime_panier', 'indemnite_km',
                  'prime_anciennete', 'numero_securite_sociale', 'num_permis',
                  'permis_valide', 'agence', 'user_id')
        read_only_fields = ('id',)
    
    def validate_matricule(self, value):
        if Employe.objects.filter(matricule=value).exists():
            raise serializers.ValidationError("Ce matricule existe déjà")
        return value
    
    def validate_email(self, value):
        if Employe.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé")
        return value
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id', None)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                validated_data['user'] = user
            except User.DoesNotExist:
                pass
        return super().create(validated_data)


# ============================================================
# EMPLOYE COMPETENCE SERIALIZER
# ============================================================

class EmployeCompetenceSerializer(serializers.ModelSerializer):
    competence_nom = serializers.CharField(source='competence.nom', read_only=True)
    competence_categorie = serializers.CharField(source='competence.categorie', read_only=True)
    niveau_display = serializers.CharField(source='get_niveau_display', read_only=True)
    
    class Meta:
        model = EmployeCompetence
        fields = ('id', 'employe', 'competence', 'competence_nom', 
                  'competence_categorie', 'niveau', 'niveau_display',
                  'date_obtention', 'date_expiration', 'valide')
        read_only_fields = ('id',)


# ============================================================
# FORMATION SERIALIZER
# ============================================================

class FormationSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    
    class Meta:
        model = Formation
        fields = ('id', 'employe', 'employe_nom', 'nom', 'organisme',
                  'date_debut', 'date_fin', 'duree_heures', 'cout',
                  'certificat', 'valide')
        read_only_fields = ('id',)


# ============================================================
# POINTAGE SERIALIZER
# ============================================================

class PointageSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_pointage_display', read_only=True)
    projet_nom = serializers.CharField(source='projet.nom', read_only=True, default=None)
    tache_nom = serializers.CharField(source='tache.nom', read_only=True, default=None)
    
    class Meta:
        model = Pointage
        fields = ('id', 'employe', 'employe_nom', 'projet', 'projet_nom',
                  'tache', 'tache_nom', 'date', 'heure', 'type_pointage',
                  'type_display', 'latitude', 'longitude', 'remarque')
        read_only_fields = ('id', 'date', 'heure')


class PointageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pointage
        fields = ('id', 'employe', 'projet', 'tache', 'type_pointage',
                  'latitude', 'longitude', 'remarque')
        read_only_fields = ('id',)


# ============================================================
# HEURE TRAVAIL SERIALIZER
# ============================================================

class HeureTravailSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    projet_nom = serializers.CharField(source='projet.nom', read_only=True, default=None)
    total_heures = serializers.SerializerMethodField()
    
    class Meta:
        model = HeureTravail
        fields = ('id', 'employe', 'employe_nom', 'projet', 'projet_nom',
                  'tache', 'date', 'heures_normales', 'heures_supplementaires',
                  'heures_nuit', 'heures_weekend', 'total_heures', 
                  'valide', 'valide_par')
        read_only_fields = ('id',)
    
    def get_total_heures(self, obj):
        return float(obj.heures_normales + obj.heures_supplementaires + 
                obj.heures_nuit + obj.heures_weekend)


class HeureTravailBulkCreateSerializer(serializers.Serializer):
    employe_id = serializers.IntegerField()
    date = serializers.DateField()
    heures_normales = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_supplementaires = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_nuit = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_weekend = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    projet_id = serializers.IntegerField(required=False, allow_null=True)
    tache_id = serializers.IntegerField(required=False, allow_null=True)


# ============================================================
# ABSENCE SERIALIZER
# ============================================================

class AbsenceSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_absence_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    approuve_par_nom = serializers.CharField(source='approuve_par.get_full_name', read_only=True, default=None)
    
    class Meta:
        model = Absence
        fields = ('id', 'employe', 'employe_nom', 'type_absence', 'type_display',
                  'date_debut', 'date_fin', 'nombre_jours', 'statut', 'statut_display',
                  'motif', 'justificatif', 'approuve_par', 'approuve_par_nom',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'nombre_jours', 'created_at', 'updated_at')


class AbsenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Absence
        fields = ('id', 'employe', 'type_absence', 'date_debut', 'date_fin',
                  'motif', 'justificatif')
        read_only_fields = ('id',)
    
    def validate(self, data):
        if data['date_debut'] > data['date_fin']:
            raise serializers.ValidationError("La date de début doit être antérieure à la date de fin")
        
        existing = Absence.objects.filter(
            employe=data['employe'],
            statut__in=['demandee', 'approuvee'],
            date_debut__lte=data['date_fin'],
            date_fin__gte=data['date_debut']
        )
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        
        if existing.exists():
            raise serializers.ValidationError(
                "Cet employé a déjà une absence sur cette période"
            )
        
        return data


class AbsenceApproveSerializer(serializers.Serializer):
    approuve = serializers.BooleanField()
    commentaire = serializers.CharField(required=False, allow_blank=True)


# ============================================================
# NOTE DE FRAIS SERIALIZER
# ============================================================

class NoteDeFraisSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_frais_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    projet_nom = serializers.CharField(source='projet.nom', read_only=True, default=None)
    approuve_par_nom = serializers.CharField(source='approuve_par.get_full_name', read_only=True, default=None)
    
    class Meta:
        model = NoteDeFrais
        fields = ('id', 'employe', 'employe_nom', 'projet', 'projet_nom',
                  'date', 'type_frais', 'type_display', 'montant',
                  'description', 'justificatif', 'statut', 'statut_display',
                  'date_soumission', 'date_approbation', 'approuve_par',
                  'approuve_par_nom', 'commentaire', 'created_at', 'updated_at')
        read_only_fields = ('id', 'date_soumission', 'date_approbation', 
                           'created_at', 'updated_at')


class NoteDeFraisCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteDeFrais
        fields = ('id', 'employe', 'projet', 'date', 'type_frais',
                  'montant', 'description', 'justificatif')
        read_only_fields = ('id',)


class NoteDeFraisApproveSerializer(serializers.Serializer):
    approuve = serializers.BooleanField()
    commentaire = serializers.CharField(required=False, allow_blank=True)


# ============================================================
# PLANNING EMPLOYE SERIALIZER
# ============================================================

class PlanningEmployeSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    projet_nom = serializers.CharField(source='projet.nom', read_only=True, default=None)
    tache_nom = serializers.CharField(source='tache.nom', read_only=True, default=None)
    
    class Meta:
        model = PlanningEmploye
        fields = ('id', 'employe', 'employe_nom', 'projet', 'projet_nom',
                  'tache', 'tache_nom', 'date', 'heure_debut', 'heure_fin',
                  'duree_heures', 'notes', 'valide')
        read_only_fields = ('id', 'duree_heures')


# ============================================================
# DPAE SERIALIZER
# ============================================================

class DPAESerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)
    
    class Meta:
        model = DPAE
        fields = ('id', 'employe', 'employe_nom', 'numero', 'date_envoi',
                  'date_embauche', 'date_fin_contrat', 'motif_embauche',
                  'transmis', 'numero_ursaff')
        read_only_fields = ('id', 'date_envoi')


class DPAECreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPAE
        fields = ('id', 'employe', 'date_embauche', 'date_fin_contrat',
                  'motif_embauche')
        read_only_fields = ('id',)
    
    def validate(self, data):
        if data.get('date_fin_contrat') and data['date_fin_contrat'] < data['date_embauche']:
            raise serializers.ValidationError(
                "La date de fin de contrat doit être postérieure à la date d'embauche"
            )
        return data


# ============================================================
# STATISTIQUES SERIALIZER
# ============================================================

class RHStatsSerializer(serializers.Serializer):
    total_employes = serializers.IntegerField()
    actifs = serializers.IntegerField()
    inactifs = serializers.IntegerField()
    par_contrat = serializers.DictField()
    par_service = serializers.DictField()
    par_poste = serializers.DictField()
    absences_mois = serializers.IntegerField()
    formations_mois = serializers.IntegerField()