# users/serializers.py
"""
Serializers pour l'application users BTP
Gestion des utilisateurs, agences et rôles
"""

from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from .models import Agence, RoleAgence, CustomUser

User = get_user_model()


# ============================================================
# LOGIN SERIALIZER
# ============================================================

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret.pop('password', None)
        return ret

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get(
                'request'), email=email, password=password)

            if not user:
                raise serializers.ValidationError(
                    "Impossible de se connecter avec ces identifiants", code='authorization')

            if not user.is_active:
                raise serializers.ValidationError(
                    "Ce compte utilisateur est désactivé", code='authorization')

            attrs['user'] = user
        else:
            raise serializers.ValidationError(
                "Email et mot de passe sont requis", code='authorization')

        return attrs


# ============================================================
# REGISTER SERIALIZER
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):
    role_global = serializers.ChoiceField(
        choices=CustomUser.ROLE_GLOBAL_CHOICES, required=False)
    agence_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)
    role_agence = serializers.ChoiceField(
        choices=RoleAgence.ROLE_CHOICES, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name',
                  'role_global', 'agence_id', 'role_agence', 'phone',
                  'address', 'city', 'employee_id', 'hire_date', 'contract_type',
                  'specialite_principale', 'habilitations', 'certifications')
        extra_kwargs = {
            'password': {'write_only': True},
            'role_global': {'required': False, 'default': 'autre'},
            'agence_id': {'required': False, 'allow_null': True},
            'role_agence': {'required': False, 'allow_null': True},
            'employee_id': {'required': False, 'allow_null': True},  # ✅ AJOUTÉ
        }

    # ✅ VALIDATION SPÉCIFIQUE POUR employee_id
    def validate_employee_id(self, value):
        """Vérifie que le matricule n'est pas déjà utilisé"""
        if value:
            # Vérifier si le matricule existe déjà
            if User.objects.filter(employee_id=value).exists():
                raise serializers.ValidationError(
                    "Ce matricule est déjà utilisé par un autre utilisateur"
                )
        return value

    def validate(self, data):
        role_global = data.get('role_global', 'autre')

        if role_global == 'pdg':
            data.pop('agence_id', None)
            data.pop('role_agence', None)
            return data

        if role_global == 'autre':
            agence_id = data.get('agence_id')
            role_agence = data.get('role_agence')

            if not agence_id:
                raise serializers.ValidationError(
                    {'agence_id': 'L\'agence est obligatoire pour cet utilisateur'})

            if not role_agence:
                raise serializers.ValidationError(
                    {'role_agence': 'Le rôle dans l\'agence est obligatoire'})

            try:
                agence = Agence.objects.get(id=agence_id, est_active=True)
            except Agence.DoesNotExist:
                raise serializers.ValidationError(
                    {'agence_id': 'Agence non trouvée ou inactive'})

            roles_disponibles = [r[0] for r in agence.get_roles_disponibles()]
            if role_agence not in roles_disponibles:
                raise serializers.ValidationError({
                    'role_agence': f'Ce rôle n\'est pas disponible. Rôles disponibles: {", ".join(roles_disponibles)}'
                })

        return data

    def create(self, validated_data):
        agence_id = validated_data.pop('agence_id', None)
        role_agence = validated_data.pop('role_agence', None)

        if 'role_global' not in validated_data:
            validated_data['role_global'] = 'autre'

        # ✅ GÉRER LE MATRICULE : si vide ou chaîne vide, mettre à None
        if 'employee_id' in validated_data:
            if validated_data['employee_id'] == '' or validated_data['employee_id'] is None:
                validated_data['employee_id'] = None

        user = User.objects.create_user(**validated_data)

        if agence_id and role_agence and user.role_global == 'autre':
            try:
                agence = Agence.objects.get(id=agence_id)
                RoleAgence.objects.create(
                    user=user, agence=agence, role=role_agence, est_actif=True)
                user.agence_principale = agence
                user.save(update_fields=['agence_principale'])
            except Agence.DoesNotExist:
                pass

        return user


# ============================================================
# AGENCE SIMPLE SERIALIZER
# ============================================================

class AgenceSimpleSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source='get_type_agence_display', read_only=True)
    roles_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Agence
        fields = ('id', 'nom', 'code', 'type_agence',
                  'type_display', 'ville', 'est_active', 'roles_disponibles')

    def get_roles_disponibles(self, obj):
        return [{'value': r[0], 'label': r[1]} for r in obj.get_roles_disponibles()]


# ============================================================
# USER SERIALIZER
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    role_global_display = serializers.CharField(
        source='get_role_global_display', read_only=True)
    agences = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    roles_agence = serializers.SerializerMethodField()

    est_directeur_agence = serializers.SerializerMethodField()
    est_chef_chantier = serializers.SerializerMethodField()
    est_conducteur_travaux = serializers.SerializerMethodField()
    est_gestionnaire_stock = serializers.SerializerMethodField()
    est_commercial_btp = serializers.SerializerMethodField()
    est_comptable_btp = serializers.SerializerMethodField()
    est_responsable_hse = serializers.SerializerMethodField()
    est_responsable_rh = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name',
                  'role_global', 'role_global_display', 'agences', 'roles_agence',
                  'is_active', 'est_directeur_agence', 'est_chef_chantier',
                  'est_conducteur_travaux', 'est_gestionnaire_stock',
                  'est_commercial_btp', 'est_comptable_btp',
                  'est_responsable_hse', 'est_responsable_rh')
        read_only_fields = ('id', 'email')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_agences(self, obj):
        if obj.est_pdg():
            agences = Agence.objects.filter(est_active=True)
            return AgenceSimpleSerializer(agences, many=True).data
        else:
            roles = obj.roles_agence.filter(
                est_actif=True).select_related('agence')
            return AgenceSimpleSerializer([role.agence for role in roles], many=True).data

    def get_roles_agence(self, obj):
        roles = obj.roles_agence.filter(
            est_actif=True).select_related('agence')
        return [
            {
                'id': role.id,
                'agence_id': role.agence.id,
                'agence_nom': role.agence.nom,
                'agence_type': role.agence.type_agence,
                'role': role.role,
                'role_display': role.get_role_display(),
                'est_actif': role.est_actif,
                'habilitations': role.habilitations,
                'certifications': role.certifications,
                'specialites': role.specialites,
            }
            for role in roles
        ]

    def get_est_directeur_agence(self, obj):
        return obj.est_directeur_agence()

    def get_est_chef_chantier(self, obj):
        return obj.est_chef_chantier()

    def get_est_conducteur_travaux(self, obj):
        return obj.est_conducteur_travaux()

    def get_est_gestionnaire_stock(self, obj):
        return obj.est_gestionnaire_stock()

    def get_est_commercial_btp(self, obj):
        return obj.est_commercial_btp()

    def get_est_comptable_btp(self, obj):
        return obj.est_comptable_btp()

    def get_est_responsable_hse(self, obj):
        return obj.est_responsable_hse()

    def get_est_responsable_rh(self, obj):
        return obj.est_responsable_rh()


# ============================================================
# USER DETAIL SERIALIZER
# ============================================================

class UserDetailSerializer(serializers.ModelSerializer):
    role_global_display = serializers.CharField(
        source='get_role_global_display', read_only=True)
    agences = serializers.SerializerMethodField()
    roles_agence = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(
        source='created_by.email', read_only=True, default=None)
    full_name = serializers.SerializerMethodField()

    est_directeur_agence = serializers.SerializerMethodField()
    est_chef_chantier = serializers.SerializerMethodField()
    est_conducteur_travaux = serializers.SerializerMethodField()
    est_gestionnaire_stock = serializers.SerializerMethodField()
    est_commercial_btp = serializers.SerializerMethodField()
    est_comptable_btp = serializers.SerializerMethodField()
    est_responsable_hse = serializers.SerializerMethodField()
    est_responsable_rh = serializers.SerializerMethodField()
    est_assistant_rh = serializers.SerializerMethodField()
    est_formateur = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'username',
                  'role_global', 'role_global_display', 'agences', 'roles_agence',
                  'birthday', 'phone', 'address', 'city', 'country', 'postal_code',
                  'employee_id', 'hire_date', 'contract_type', 'contract_end_date',
                  'probation_end_date', 'salary', 'taux_horaire', 'prime_panier',
                  'indemnite_km', 'prime_anciennete', 'specialite_principale',
                  'specialites_secondaires', 'numero_securite_sociale',
                  'num_permis', 'permis_valide', 'cartes_professionnelles',
                  'competences', 'habilitations', 'certifications',
                  'formations_suivies', 'formations_requises',
                  'visite_medicale_date', 'prochaine_visite_medicale',
                  'aptitude_medicale', 'restrictions_medicales', 'documents_rh',
                  'dernier_entretien', 'prochain_entretien', 'evaluation_annuelle',
                  'disponible', 'disponible_date_debut', 'disponible_date_fin',
                  'is_active', 'is_staff', 'is_superuser', 'created_at', 'updated_at',
                  'created_by_email', 'agence_principale', 'last_login', 'date_joined',
                  'est_directeur_agence', 'est_chef_chantier', 'est_conducteur_travaux',
                  'est_gestionnaire_stock', 'est_commercial_btp', 'est_comptable_btp',
                  'est_responsable_hse', 'est_responsable_rh', 'est_assistant_rh',
                  'est_formateur')
        read_only_fields = ('id', 'is_staff', 'is_superuser',
                            'created_at', 'updated_at', 'last_login', 'date_joined')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_agences(self, obj):
        if obj.est_pdg():
            agences = Agence.objects.filter(est_active=True)
            return AgenceSerializer(agences, many=True, context=self.context).data
        else:
            agences = obj.get_agences()
            return AgenceSerializer(agences, many=True, context=self.context).data

    def get_roles_agence(self, obj):
        if obj.est_pdg():
            return []
        roles = obj.roles_agence.filter(
            est_actif=True).select_related('agence')
        return [
            {
                'id': role.id,
                'agence_id': role.agence.id,
                'agence_nom': role.agence.nom,
                'agence_type': role.agence.type_agence,
                'role': role.role,
                'role_display': role.get_role_display(),
                'est_actif': role.est_actif,
                'date_attribution': role.date_attribution,
                'habilitations': role.habilitations,
                'certifications': role.certifications,
                'specialites': role.specialites,
            }
            for role in roles
        ]

    def get_est_directeur_agence(self, obj):
        return obj.est_directeur_agence()

    def get_est_chef_chantier(self, obj):
        return obj.est_chef_chantier()

    def get_est_conducteur_travaux(self, obj):
        return obj.est_conducteur_travaux()

    def get_est_gestionnaire_stock(self, obj):
        return obj.est_gestionnaire_stock()

    def get_est_commercial_btp(self, obj):
        return obj.est_commercial_btp()

    def get_est_comptable_btp(self, obj):
        return obj.est_comptable_btp()

    def get_est_responsable_hse(self, obj):
        return obj.est_responsable_hse()

    def get_est_responsable_rh(self, obj):
        return obj.est_responsable_rh()

    def get_est_assistant_rh(self, obj):
        return obj.est_assistant_rh()

    def get_est_formateur(self, obj):
        return obj.est_formateur()


# ============================================================
# AGENCE SERIALIZER
# ============================================================

class AgenceSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source='get_type_agence_display', read_only=True)
    roles_disponibles = serializers.SerializerMethodField()
    nombre_utilisateurs = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(
        source='created_by.email', read_only=True, default=None)

    nombre_directeurs = serializers.SerializerMethodField()
    nombre_chefs_chantier = serializers.SerializerMethodField()
    nombre_conducteurs = serializers.SerializerMethodField()
    nombre_gestionnaires_stock = serializers.SerializerMethodField()
    nombre_commerciaux = serializers.SerializerMethodField()
    nombre_comptables = serializers.SerializerMethodField()
    nombre_responsables_hse = serializers.SerializerMethodField()
    nombre_responsables_rh = serializers.SerializerMethodField()

    class Meta:
        model = Agence
        fields = ('id', 'nom', 'code', 'type_agence', 'type_display', 'region',
                  'adresse', 'telephone', 'email', 'ville', 'code_postal', 'pays',
                  'coordonnees_gps', 'superficie_m2', 'capacite_stockage',
                  'nb_engins_max', 'nb_employes_max', 'est_active',
                  'roles_disponibles', 'nombre_utilisateurs', 'date_creation',
                  'date_modification', 'created_by_email',
                  'nombre_directeurs', 'nombre_chefs_chantier', 'nombre_conducteurs',
                  'nombre_gestionnaires_stock', 'nombre_commerciaux',
                  'nombre_comptables', 'nombre_responsables_hse', 'nombre_responsables_rh')
        read_only_fields = ('id', 'code', 'date_creation', 'date_modification')

    def get_roles_disponibles(self, obj):
        return [{'value': r[0], 'label': r[1]} for r in obj.get_roles_disponibles()]

    def get_nombre_utilisateurs(self, obj):
        return obj.roles.filter(est_actif=True).count()

    def get_nombre_directeurs(self, obj):
        return obj.roles.filter(role='directeur_agence', est_actif=True).count()

    def get_nombre_chefs_chantier(self, obj):
        return obj.roles.filter(role='chef_chantier', est_actif=True).count()

    def get_nombre_conducteurs(self, obj):
        return obj.roles.filter(role='conducteur_travaux', est_actif=True).count()

    def get_nombre_gestionnaires_stock(self, obj):
        return obj.roles.filter(role='gestionnaire_stock', est_actif=True).count()

    def get_nombre_commerciaux(self, obj):
        return obj.roles.filter(role='commercial_btp', est_actif=True).count()

    def get_nombre_comptables(self, obj):
        return obj.roles.filter(role='comptable_btp', est_actif=True).count()

    def get_nombre_responsables_hse(self, obj):
        return obj.roles.filter(role='responsable_hse', est_actif=True).count()

    def get_nombre_responsables_rh(self, obj):
        return obj.roles.filter(role='responsable_rh', est_actif=True).count()


class AgenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agence
        fields = ('id', 'nom', 'type_agence', 'region', 'adresse', 'telephone',
                  'email', 'ville', 'code_postal', 'pays', 'superficie_m2',
                  'capacite_stockage', 'nb_engins_max', 'nb_employes_max')

    def validate_nom(self, value):
        if Agence.objects.filter(nom__iexact=value).exists():
            raise serializers.ValidationError(
                "Une agence avec ce nom existe déjà")
        return value


# ============================================================
# ROLE AGENCE SERIALIZER
# ============================================================

class RoleAgenceSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    agence_nom = serializers.CharField(source='agence.nom', read_only=True)
    agence_type = serializers.CharField(
        source='agence.type_agence', read_only=True)
    role_display = serializers.CharField(
        source='get_role_display', read_only=True)
    role_disponible = serializers.SerializerMethodField()

    class Meta:
        model = RoleAgence
        fields = ('id', 'user', 'user_email', 'user_name', 'agence', 'agence_nom',
                  'agence_type', 'role', 'role_display', 'est_actif',
                  'date_attribution', 'date_fin', 'role_disponible',
                  'habilitations', 'certifications', 'specialites')
        read_only_fields = ('id', 'date_attribution')

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_role_disponible(self, obj):
        roles_disponibles = [r[0] for r in obj.agence.get_roles_disponibles()]
        return obj.role in roles_disponibles

    def validate(self, data):
        user = data.get('user')
        agence = data.get('agence')
        role = data.get('role')

        if user and agence and role:
            if RoleAgence.objects.filter(user=user, agence=agence, role=role, est_actif=True).exists():
                raise serializers.ValidationError(
                    f"L'utilisateur a déjà le rôle {role} dans cette agence")

            roles_disponibles = [r[0] for r in agence.get_roles_disponibles()]
            if role not in roles_disponibles:
                raise serializers.ValidationError(
                    f"Le rôle '{role}' n'est pas disponible pour cette agence. "
                    f"Rôles disponibles: {', '.join(roles_disponibles)}"
                )

            if user.est_pdg():
                raise serializers.ValidationError(
                    "Le PDG n'a pas de rôles spécifiques par agence")

        return data


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    agence_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=RoleAgence.ROLE_CHOICES)

    def validate(self, data):
        try:
            user = User.objects.get(id=data['user_id'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'user_id': 'Utilisateur non trouvé'})

        try:
            agence = Agence.objects.get(id=data['agence_id'], est_active=True)
        except Agence.DoesNotExist:
            raise serializers.ValidationError(
                {'agence_id': 'Agence non trouvée ou inactive'})

        roles_disponibles = [r[0] for r in agence.get_roles_disponibles()]
        if data['role'] not in roles_disponibles:
            raise serializers.ValidationError(
                {'role': f'Rôle non disponible. Rôles disponibles: {", ".join(roles_disponibles)}'})

        if user.est_pdg():
            raise serializers.ValidationError(
                "Le PDG n'a pas de rôles d'agence")

        if RoleAgence.objects.filter(user=user, agence=agence, role=data['role'], est_actif=True).exists():
            raise serializers.ValidationError(
                {'role': f'L\'utilisateur a déjà ce rôle dans cette agence'})

        data['user'] = user
        data['agence'] = agence
        return data

    def create(self, validated_data):
        return RoleAgence.objects.create(
            user=validated_data['user'],
            agence=validated_data['agence'],
            role=validated_data['role'],
            est_actif=True
        )