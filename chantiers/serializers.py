# chantiers/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from decimal import Decimal
from .models import (
    Projet, Phase, Tache, AffectationTache,
    SousTraitant, InterventionSousTraitant,
    DocumentChantier, RapportQuotidien
)

User = get_user_model()


# ============================================================
# SOUS-TRAITANTS
# ============================================================

class SousTraitantSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_entreprise_display', read_only=True)
    
    class Meta:
        model = SousTraitant
        fields = ('id', 'nom', 'siret', 'type_entreprise', 'type_display',
                  'email', 'telephone', 'adresse', 'ville', 'code_postal',
                  'contact_nom', 'contact_telephone', 'contact_email',
                  'note', 'actif', 'created_at')
        read_only_fields = ('id', 'created_at')


class SousTraitantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SousTraitant
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


# ============================================================
# PROJET
# ============================================================

class PhaseSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = ('id', 'nom', 'type_phase', 'ordre', 'taux_avancement', 'date_debut', 'date_fin_previsionnelle')


class ProjetSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_projet_display', read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    chef_projet_nom = serializers.CharField(source='chef_projet.get_full_name', read_only=True, default=None)
    cout_total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    marge_reelle = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    nb_phases = serializers.SerializerMethodField()
    nb_taches = serializers.SerializerMethodField()
    
    class Meta:
        model = Projet
        fields = ('id', 'code', 'nom', 'type_projet', 'type_display', 'statut', 'statut_display',
                  'client', 'client_nom', 'chef_projet', 'chef_projet_nom', 'agence', 'agence_nom',
                  'date_debut', 'date_fin_previsionnelle', 'date_fin_reelle', 'duree_jours',
                  'budget_total', 'budget_mo', 'budget_materiaux', 'budget_sous_traitance', 'budget_frais_generaux',
                  'cout_reel_mo', 'cout_reel_materiaux', 'cout_reel_sous_traitance', 'cout_reel_frais_generaux',
                  'cout_total', 'marge_reelle',
                  'adresse_chantier', 'code_postal', 'ville', 'coordonnees_gps',
                  'taux_avancement', 'rentabilite_previsionnelle', 'note_qualite', 'niveau_risque',
                  'nb_phases', 'nb_taches',
                  'created_at', 'updated_at', 'created_by')
        read_only_fields = ('id', 'created_at', 'updated_at', 'duree_jours',
                            'cout_reel_mo', 'cout_reel_materiaux', 'cout_reel_sous_traitance',
                            'cout_reel_frais_generaux')

    def get_nb_phases(self, obj):
        return obj.phases.count()

    def get_nb_taches(self, obj):
        return Tache.objects.filter(phase__projet=obj).count()


class ProjetDetailSerializer(ProjetSerializer):
    phases = PhaseSimpleSerializer(many=True, read_only=True)
    interventions_st = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    
    class Meta(ProjetSerializer.Meta):
        fields = ProjetSerializer.Meta.fields + ('phases', 'interventions_st', 'documents')

    def get_interventions_st(self, obj):
        interventions = obj.interventions_st.all()
        return InterventionSousTraitantSerializer(interventions, many=True).data

    def get_documents(self, obj):
        docs = obj.documents.all()
        return DocumentChantierSerializer(docs, many=True).data

class ProjetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projet
        fields = ('id', 'code', 'nom', 'type_projet', 'statut', 'client',
                  'chef_projet', 'agence', 'date_debut', 'date_fin_previsionnelle',
                  'budget_total', 'budget_mo', 'budget_materiaux', 'budget_sous_traitance',
                  'budget_frais_generaux', 'adresse_chantier', 'code_postal', 'ville',
                  'coordonnees_gps', 'taux_avancement', 'rentabilite_previsionnelle',
                  'note_qualite', 'niveau_risque')
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('date_debut') and data.get('date_fin_previsionnelle'):
            if data['date_fin_previsionnelle'] < data['date_debut']:
                raise serializers.ValidationError(
                    {'date_fin_previsionnelle': 'La date de fin doit être postérieure à la date de début'}
                )
        return data

# ============================================================
# PHASE
# ============================================================

class PhaseSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_phase_display', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    nb_taches = serializers.SerializerMethodField()
    projet_code = serializers.CharField(source='projet.code', read_only=True)
    
    class Meta:
        model = Phase
        fields = ('id', 'projet', 'projet_code', 'nom', 'type_phase', 'type_display',
                  'ordre', 'date_debut', 'date_fin_previsionnelle', 'date_fin_reelle',
                  'budget', 'cout_reel', 'taux_avancement',
                  'responsable', 'responsable_nom', 'nb_taches')
        read_only_fields = ('id', 'cout_reel')

    def get_nb_taches(self, obj):
        return obj.taches.count()


class PhaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = '__all__'
        read_only_fields = ('id', 'cout_reel')

    def validate(self, data):
        if data.get('date_debut') and data.get('date_fin_previsionnelle'):
            if data['date_fin_previsionnelle'] < data['date_debut']:
                raise serializers.ValidationError(
                    {'date_fin_previsionnelle': 'La date de fin doit être postérieure à la date de début'}
                )
        return data


# ============================================================
# TÂCHE
# ============================================================

class TacheSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    phase_nom = serializers.CharField(source='phase.nom', read_only=True)
    projet_code = serializers.CharField(source='phase.projet.code', read_only=True)
    nb_affectations = serializers.SerializerMethodField()
    
    class Meta:
        model = Tache
        fields = ('id', 'phase', 'phase_nom', 'projet_code', 'nom', 'description',
                  'priorite', 'priorite_display', 'statut', 'statut_display',
                  'date_debut', 'date_fin_previsionnelle', 'date_fin_reelle',
                  'duree_estimee', 'responsable', 'responsable_nom',
                  'cout_estime', 'cout_reel', 'nb_affectations',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'cout_reel', 'created_at', 'updated_at')

    def get_nb_affectations(self, obj):
        return obj.affectationtache_set.count()


class TacheCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tache
        fields = ('id', 'phase', 'nom', 'description', 'priorite', 'statut',
                  'date_debut', 'date_fin_previsionnelle', 'duree_estimee',
                  'responsable', 'cout_estime')
        read_only_fields = ('id', 'cout_reel')


class TacheDetailSerializer(TacheSerializer):
    affectations = serializers.SerializerMethodField()
    dependances = TacheSerializer(many=True, read_only=True)
    
    class Meta(TacheSerializer.Meta):
        fields = TacheSerializer.Meta.fields + ('affectations', 'dependances')

    def get_affectations(self, obj):
        affectations = obj.affectationtache_set.all()
        return AffectationTacheSerializer(affectations, many=True).data


# ============================================================
# AFFECTATION TÂCHE
# ============================================================

class AffectationTacheSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True, default=None)
    tache_nom = serializers.CharField(source='tache.nom', read_only=True)
    
    class Meta:
        model = AffectationTache
        fields = ('id', 'tache', 'tache_nom', 'employe', 'employe_nom',
                  'heures_prevues', 'heures_reelles', 'date_debut', 'date_fin', 'role')
        read_only_fields = ('id', 'heures_reelles')


class AffectationTacheCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffectationTache
        fields = '__all__'
        read_only_fields = ('id', 'heures_reelles')


# ============================================================
# INTERVENTION SOUS-TRAITANT
# ============================================================

class InterventionSousTraitantSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    sous_traitant_nom = serializers.CharField(source='sous_traitant.nom', read_only=True)
    projet_code = serializers.CharField(source='projet.code', read_only=True)
    phase_nom = serializers.CharField(source='phase.nom', read_only=True, default=None)
    
    class Meta:
        model = InterventionSousTraitant
        fields = ('id', 'sous_traitant', 'sous_traitant_nom', 'projet', 'projet_code',
                  'phase', 'phase_nom', 'description', 'montant_estime', 'montant_reel',
                  'date_debut', 'date_fin', 'statut', 'statut_display',
                  'bon_commande', 'facture', 'created_at')
        read_only_fields = ('id', 'created_at')


class InterventionSousTraitantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSousTraitant
        fields = '__all__'
        read_only_fields = ('id', 'montant_reel', 'created_at')


# ============================================================
# DOCUMENT CHANTIER
# ============================================================

class DocumentChantierSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_document_display', read_only=True)
    auteur_nom = serializers.CharField(source='auteur.get_full_name', read_only=True, default=None)
    projet_code = serializers.CharField(source='projet.code', read_only=True)
    
    class Meta:
        model = DocumentChantier
        fields = ('id', 'projet', 'projet_code', 'type_document', 'type_display',
                  'nom', 'fichier', 'version', 'description', 'auteur', 'auteur_nom',
                  'date_upload')
        read_only_fields = ('id', 'date_upload')


class DocumentChantierCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChantier
        fields = '__all__'
        read_only_fields = ('id', 'date_upload')


# ============================================================
# RAPPORT QUOTIDIEN
# ============================================================

class RapportQuotidienSerializer(serializers.ModelSerializer):
    redacteur_nom = serializers.CharField(source='redacteur.get_full_name', read_only=True, default=None)
    projet_code = serializers.CharField(source='projet.code', read_only=True)
    
    class Meta:
        model = RapportQuotidien
        fields = ('id', 'projet', 'projet_code', 'date', 'redacteur', 'redacteur_nom',
                  'conditions_meteo', 'effectif_present', 'travaux_realises',
                  'travaux_prevus', 'difficultes', 'securite', 'materiel_utilise',
                  'observations', 'signe_chef_chantier', 'signe_client', 'created_at')
        read_only_fields = ('id', 'created_at')


class RapportQuotidienCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RapportQuotidien
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


# ============================================================
# STATISTIQUES CHANTIERS
# ============================================================

class ChantierStatsSerializer(serializers.Serializer):
    total_projets = serializers.IntegerField()
    par_statut = serializers.DictField()
    par_type = serializers.DictField()
    budget_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    cout_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    taux_avancement_moyen = serializers.DecimalField(max_digits=5, decimal_places=2)
    projets_retard = serializers.IntegerField()
    projets_termines = serializers.IntegerField()