# crm/serializers.py
"""
Serializers pour l'application CRM - Multi-agences
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from .models import Client, Lead, Interaction, AppelOffre

User = get_user_model()


# ============================================================
# CLIENT SERIALIZER
# ============================================================

class ClientSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_client_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    nb_projets = serializers.SerializerMethodField()
    nb_appels_offres = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = ('id', 'agence', 'agence_nom', 'nom', 'type_client', 'type_display', 'siret',
                  'email', 'telephone', 'adresse', 'code_postal', 'ville', 'pays',
                  'contact_principal', 'contact_telephone', 'contact_email',
                  'numero_compte', 'plafond_credit', 'actif', 'note',
                  'nb_projets', 'nb_appels_offres',
                  'created_at', 'updated_at', 'created_by', 'created_by_name')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_nb_projets(self, obj):
        return obj.projets.count() if hasattr(obj, 'projets') else 0
    
    def get_nb_appels_offres(self, obj):
        return obj.appels_offres.count()


class ClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ('id', 'agence', 'nom', 'type_client', 'siret', 'email', 'telephone',
                  'adresse', 'code_postal', 'ville', 'pays',
                  'contact_principal', 'contact_telephone', 'contact_email',
                  'numero_compte', 'plafond_credit', 'actif', 'note')
        read_only_fields = ('id',)
    
    def validate(self, data):
        # ✅ Vérifier l'unicité par agence
        if data.get('agence') and data.get('email'):
            if Client.objects.filter(agence=data['agence'], email=data['email']).exists():
                raise serializers.ValidationError(
                    {'email': 'Un client avec cet email existe déjà dans cette agence'}
                )
        return data
    
    def validate_siret(self, value):
        if value and Client.objects.filter(siret=value).exists():
            raise serializers.ValidationError("Ce SIRET est déjà utilisé")
        return value


class ClientDetailSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_client_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    leads = serializers.SerializerMethodField()
    appels_offres = serializers.SerializerMethodField()
    interactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = ('id', 'agence', 'agence_nom', 'nom', 'type_client', 'type_display', 'siret',
                  'email', 'telephone', 'adresse', 'code_postal', 'ville', 'pays',
                  'contact_principal', 'contact_telephone', 'contact_email',
                  'numero_compte', 'plafond_credit', 'actif', 'note',
                  'leads', 'appels_offres', 'interactions',
                  'created_at', 'updated_at', 'created_by', 'created_by_name')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_leads(self, obj):
        leads = obj.leads.all()
        return LeadSerializer(leads, many=True).data
    
    def get_appels_offres(self, obj):
        appels = obj.appels_offres.all()
        return AppelOffreSerializer(appels, many=True).data
    
    def get_interactions(self, obj):
        interactions = obj.interactions.all()[:10]
        return InteractionSerializer(interactions, many=True).data


# ============================================================
# LEAD SERIALIZER
# ============================================================

class LeadSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True, default=None)
    client_nom = serializers.CharField(source='client.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = ('id', 'agence', 'agence_nom', 'nom', 'email', 'telephone', 'societe',
                  'statut', 'statut_display', 'source', 'source_display',
                  'type_travaux', 'budget_estime', 'delai_souhaite',
                  'notes', 'prochaine_action',
                  'commercial', 'commercial_name', 'client', 'client_nom',
                  'age', 'created_at', 'updated_at', 'date_perte', 'motif_perte')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_age(self, obj):
        delta = date.today() - obj.created_at.date()
        return delta.days


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ('id', 'agence', 'nom', 'email', 'telephone', 'societe',
                  'statut', 'source', 'type_travaux', 'budget_estime',
                  'delai_souhaite', 'notes', 'prochaine_action',
                  'commercial', 'client')
        read_only_fields = ('id',)
    
    def validate(self, data):
        # ✅ Vérifier l'unicité par agence
        if data.get('agence') and data.get('email'):
            if Lead.objects.filter(agence=data['agence'], email=data['email']).exists():
                raise serializers.ValidationError(
                    {'email': 'Un lead avec cet email existe déjà dans cette agence'}
                )
        return data


class LeadDetailSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True, default=None)
    client_nom = serializers.CharField(source='client.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    interactions = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = ('id', 'agence', 'agence_nom', 'nom', 'email', 'telephone', 'societe',
                  'statut', 'statut_display', 'source', 'source_display',
                  'type_travaux', 'budget_estime', 'delai_souhaite',
                  'notes', 'prochaine_action',
                  'commercial', 'commercial_name', 'client', 'client_nom',
                  'interactions', 'age',
                  'created_at', 'updated_at', 'date_perte', 'motif_perte')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_interactions(self, obj):
        interactions = obj.interactions.all()[:10]
        return InteractionSerializer(interactions, many=True).data
    
    def get_age(self, obj):
        delta = date.today() - obj.created_at.date()
        return delta.days


class LeadChangeStatutSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=Lead.STATUT_CHOICES)
    motif_perte = serializers.CharField(required=False, allow_blank=True)


# ============================================================
# INTERACTION SERIALIZER
# ============================================================

class InteractionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_interaction_display', read_only=True)
    responsable_name = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    lead_nom = serializers.CharField(source='lead.nom', read_only=True, default=None)
    client_nom = serializers.CharField(source='client.nom', read_only=True, default=None)
    projet_nom = serializers.CharField(source='projet.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    
    class Meta:
        model = Interaction
        fields = ('id', 'agence', 'agence_nom', 'lead', 'lead_nom', 'client', 'client_nom',
                  'projet', 'projet_nom', 'type_interaction', 'type_display',
                  'date', 'duree', 'sujet', 'contenu',
                  'responsable', 'responsable_name')
        read_only_fields = ('id', 'date')


class InteractionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = ('id', 'agence', 'lead', 'client', 'projet', 'type_interaction',
                  'duree', 'sujet', 'contenu', 'responsable')
        read_only_fields = ('id', 'date')


# ============================================================
# APPEL D'OFFRES SERIALIZER
# ============================================================

class AppelOffreSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    responsable_name = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    client_nom = serializers.CharField(source='client.nom', read_only=True, default=None)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True, default=None)
    est_en_retard = serializers.SerializerMethodField()
    jours_restants = serializers.SerializerMethodField()
    
    class Meta:
        model = AppelOffre
        fields = ('id', 'agence', 'agence_nom', 'reference', 'client', 'client_nom',
                  'objet', 'description', 'date_publication', 'date_limite',
                  'date_soumission', 'statut', 'statut_display',
                  'budget_estime', 'montant_soumis',
                  'documents', 'notes', 'responsable', 'responsable_name',
                  'est_en_retard', 'jours_restants',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_est_en_retard(self, obj):
        if obj.statut in ['recu', 'en_cours'] and obj.date_limite:
            return date.today() > obj.date_limite
        return False
    
    def get_jours_restants(self, obj):
        if obj.statut in ['recu', 'en_cours'] and obj.date_limite:
            delta = obj.date_limite - date.today()
            return delta.days
        return None


class AppelOffreCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppelOffre
        fields = ('id', 'agence', 'reference', 'client', 'objet', 'description',
                  'date_publication', 'date_limite', 'date_soumission',
                  'statut', 'budget_estime', 'montant_soumis',
                  'documents', 'notes', 'responsable')
        read_only_fields = ('id',)
    
    def validate(self, data):
        # ✅ Vérifier l'unicité par agence
        if data.get('agence') and data.get('reference'):
            if AppelOffre.objects.filter(agence=data['agence'], reference=data['reference']).exists():
                raise serializers.ValidationError(
                    {'reference': 'Une référence avec ce numéro existe déjà dans cette agence'}
                )
        return data


class AppelOffreChangeStatutSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=AppelOffre.STATUT_CHOICES)
    montant_soumis = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


# ============================================================
# STATISTIQUES CRM SERIALIZER
# ============================================================

class CRMStatsSerializer(serializers.Serializer):
    total_clients = serializers.IntegerField()
    clients_actifs = serializers.IntegerField()
    total_leads = serializers.IntegerField()
    leads_by_statut = serializers.DictField()
    leads_by_source = serializers.DictField()
    appels_offres_en_cours = serializers.IntegerField()
    appels_offres_gagnes = serializers.IntegerField()
    interactions_mois = serializers.IntegerField()