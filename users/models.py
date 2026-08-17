from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django_rest_passwordreset.signals import reset_password_token_created
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template.loader import render_to_string


class CustomUserManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle CustomUser BTP
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est requis')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role_global', 'pdg')
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class Agence(models.Model):
    """
    Agence BTP avec caractéristiques spécifiques
    """
    
    TYPE_AGENCE_CHOICES = (
        ('siege', 'Siège Social'),
        ('regionale', 'Agence Régionale'),
        ('chantier', 'Base Vie Chantier'),
        ('logistique', 'Dépôt Logistique'),
    )
    
    REGION_CHOICES = (
        ('nord', 'Nord'),
        ('sud', 'Sud'),
        ('est', 'Est'),
        ('ouest', 'Ouest'),
        ('centre', 'Centre'),
        ('international', 'International'),
    )
    
    nom = models.CharField(max_length=200, verbose_name="Nom de l'agence")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code agence", blank=True)
    type_agence = models.CharField(max_length=20, choices=TYPE_AGENCE_CHOICES, default='regionale')
    region = models.CharField(max_length=20, choices=REGION_CHOICES, default='centre')
    
    # Adresse
    adresse = models.TextField(verbose_name="Adresse")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    email = models.EmailField(verbose_name="Email")
    ville = models.CharField(max_length=100, verbose_name="Ville")
    code_postal = models.CharField(max_length=20, verbose_name="Code postal")
    pays = models.CharField(max_length=100, default='France', verbose_name="Pays")
    coordonnees_gps = models.CharField(max_length=100, blank=True, null=True)
    
    # Spécifique BTP
    superficie_m2 = models.IntegerField(null=True, blank=True)
    capacite_stockage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    nb_engins_max = models.IntegerField(null=True, blank=True)
    nb_employes_max = models.IntegerField(null=True, blank=True)
    
    # Métadonnées
    est_active = models.BooleanField(default=True, verbose_name="Agence active")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='agences_crees', verbose_name="Créée par")
    
    class Meta:
        verbose_name = "Agence BTP"
        verbose_name_plural = "Agences BTP"
        ordering = ['-type_agence', 'region', 'nom']
        permissions = [
            ("can_create_agence", "Peut créer une agence"),
            ("can_edit_agence", "Peut modifier une agence"),
            ("can_delete_agence", "Peut supprimer une agence"),
            ("can_view_all_agences", "Peut voir toutes les agences"),
            ("can_manage_chantier", "Peut gérer les chantiers de l'agence"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.get_type_agence_display()})"

    def get_roles_disponibles(self):
        """
        Retourne les rôles disponibles selon le type d'agence
        """
        # Rôles communs à tous les types d'agences
        roles_communs = [
            ('directeur_agence', 'Directeur d\'Agence'),
            ('chef_chantier', 'Chef de Chantier'),
            ('conducteur_travaux', 'Conducteur de Travaux'),
            ('gestionnaire_stock', 'Gestionnaire de Stock'),
            ('commercial_btp', 'Commercial BTP'),
            ('comptable_btp', 'Comptable BTP'),
            ('responsable_qualite', 'Responsable Qualité'),
            ('responsable_hse', 'Responsable HSE'),
            ('acheteur', 'Acheteur'),
            # Rôles RH
            ('responsable_rh', 'Responsable RH'),
            ('assistant_rh', 'Assistant RH'),
            ('formateur', 'Formateur'),
        ]
        
        # Rôles spécifiques aux chantiers
        roles_chantier = [
            ('technicien', 'Technicien'),
            ('securite', 'Responsable Sécurité'),
            ('assistant_chantier', 'Assistant de Chantier'),
        ]
        
        if self.type_agence == 'chantier':
            return roles_communs + roles_chantier
        else:
            return roles_communs + [('assistant_admin', 'Assistant Administratif')]

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = self.type_agence[:3].upper()
            count = Agence.objects.filter(type_agence=self.type_agence).count() + 1
            self.code = f"{prefix}{self.nom[:3].upper()}{str(count).zfill(3)}"
        super().save(*args, **kwargs)


class RoleAgence(models.Model):
    """
    Rôle spécifique BTP dans une agence
    """
    
    ROLE_CHOICES = (
        # Direction
        ('directeur_agence', 'Directeur d\'Agence'),
        ('chef_chantier', 'Chef de Chantier'),
        ('conducteur_travaux', 'Conducteur de Travaux'),
        
        # Opérationnel
        ('technicien', 'Technicien'),
        
        # Support
        ('gestionnaire_stock', 'Gestionnaire de Stock'),
        ('commercial_btp', 'Commercial BTP'),
        ('comptable_btp', 'Comptable BTP'),
        ('responsable_qualite', 'Responsable Qualité'),
        ('responsable_hse', 'Responsable HSE'),
        ('acheteur', 'Acheteur'),
        ('securite', 'Responsable Sécurité'),
        
        # RH
        ('responsable_rh', 'Responsable RH'),
        ('assistant_rh', 'Assistant RH'),
        ('formateur', 'Formateur'),
        
        # Administratif
        ('assistant_chantier', 'Assistant de Chantier'),
        ('assistant_admin', 'Assistant Administratif'),
    )
    
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='roles_agence')
    agence = models.ForeignKey(Agence, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, verbose_name="Rôle BTP")
    
    # Spécifique BTP
    est_actif = models.BooleanField(default=True)
    date_attribution = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    
    # Qualifications supplémentaires
    habilitations = models.JSONField(default=list, blank=True, 
                                     help_text="Liste des habilitations (ex: ['H0V', 'BTP', 'CACES'])")
    certifications = models.JSONField(default=list, blank=True, 
                                      help_text="Liste des certifications")
    specialites = models.JSONField(default=list, blank=True, 
                                   help_text="Spécialités BTP")
    
    class Meta:
        verbose_name = "Rôle BTP par agence"
        verbose_name_plural = "Rôles BTP par agence"
        unique_together = ['user', 'agence', 'role']
        ordering = ['agence', 'role']

    def clean(self):
        roles_disponibles = [r[0] for r in self.agence.get_roles_disponibles()]
        if self.role not in roles_disponibles:
            raise ValidationError(
                f"Le rôle '{self.get_role_display()}' n'est pas disponible "
                f"pour une agence de type {self.agence.get_type_agence_display()}"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.agence.nom} : {self.get_role_display()}"


class CustomUser(AbstractUser):
    """
    Modèle utilisateur BTP avec gestion multi-agences
    
    ✅ SEUL LE PDG A UN RÔLE GLOBAL
    ✅ TOUS LES AUTRES UTILISATEURS ONT DES RÔLES PAR AGENCE
    """
    
    # Rôle global : PDG uniquement
    ROLE_GLOBAL_CHOICES = (
        ('pdg', 'PDG - Accès total sur toutes les agences'),
        ('autre', 'Autre - Rôle par agence uniquement'),
    )
    
    # Spécialités BTP
    SPECIALITE_CHOICES = (
        ('gros_oeuvre', 'Gros Œuvre'),
        ('second_oeuvre', 'Second Œuvre'),
        ('tp', 'Travaux Publics'),
        ('genie_civil', 'Génie Civil'),
        ('charpente', 'Charpente'),
        ('couverture', 'Couverture'),
        ('plomberie', 'Plomberie'),
        ('electricite', 'Électricité'),
        ('climatisation', 'Climatisation'),
        ('peinture', 'Peinture'),
        ('carrelage', 'Carrelage'),
        ('menuiserie', 'Menuiserie'),
        ('autre', 'Autre'),
    )
    
    # Identité
    email = models.EmailField(max_length=200, unique=True, verbose_name="Email")
    username = models.CharField(max_length=200, null=True, blank=True, verbose_name="Nom d'utilisateur")
    birthday = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    
    # Rôle global : uniquement PDG ou autre
    role_global = models.CharField(max_length=20, choices=ROLE_GLOBAL_CHOICES, default='autre', 
                                   verbose_name="Rôle global")
    
    # Spécialités BTP
    specialite_principale = models.CharField(max_length=30, choices=SPECIALITE_CHOICES, 
                                             null=True, blank=True, verbose_name="Spécialité principale")
    specialites_secondaires = models.JSONField(default=list, blank=True, 
                                               verbose_name="Spécialités secondaires")
    
    # Informations personnelles
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Téléphone")
    address = models.TextField(null=True, blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Ville")
    country = models.CharField(max_length=100, null=True, blank=True, default='France', 
                               verbose_name="Pays")
    postal_code = models.CharField(max_length=20, null=True, blank=True, verbose_name="Code postal")
    
    # ==================== INFORMATIONS RH BTP ====================
    
    # Contrat
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True, 
                                   verbose_name="Matricule")
    hire_date = models.DateField(null=True, blank=True, verbose_name="Date d'embauche")
    contract_type = models.CharField(max_length=50, null=True, blank=True, 
                                     choices=[
                                         ('cdi', 'CDI'),
                                         ('cdd', 'CDD'),
                                         ('interim', 'Intérim'),
                                         ('apprenti', 'Apprenti'),
                                         ('stagiaire', 'Stagiaire'),
                                         ('auto_entrepreneur', 'Auto-Entrepreneur'),
                                         ('portage', 'Portage Salarial'),
                                     ], verbose_name="Type de contrat")
    contract_end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin de contrat")
    probation_end_date = models.DateField(null=True, blank=True, verbose_name="Fin de période d'essai")
    
    # Salaire
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                 verbose_name="Salaire mensuel")
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                       verbose_name="Taux horaire")
    prime_panier = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                       verbose_name="Prime panier")
    indemnite_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                       verbose_name="Indemnité kilométrique")
    prime_anciennete = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                           verbose_name="Prime d'ancienneté")
    
    # Qualifications et habilitations BTP
    numero_securite_sociale = models.CharField(max_length=15, blank=True, 
                                               verbose_name="Numéro de sécurité sociale")
    num_permis = models.CharField(max_length=20, blank=True, verbose_name="Numéro de permis")
    permis_valide = models.BooleanField(default=True, verbose_name="Permis valide")
    cartes_professionnelles = models.JSONField(default=list, blank=True, 
                                               verbose_name="Cartes professionnelles")
    
    # Compétences et formations
    competences = models.JSONField(default=list, blank=True, verbose_name="Compétences")
    habilitations = models.JSONField(default=list, blank=True, 
                                     verbose_name="Habilitations (ex: CACES, H0V...)")
    certifications = models.JSONField(default=list, blank=True, 
                                      verbose_name="Certifications professionnelles")
    formations_suivies = models.JSONField(default=list, blank=True, 
                                          verbose_name="Formations suivies")
    formations_requises = models.JSONField(default=list, blank=True, 
                                           verbose_name="Formations obligatoires à suivre")
    
    # Santé et sécurité
    visite_medicale_date = models.DateField(null=True, blank=True, 
                                            verbose_name="Date de la dernière visite médicale")
    prochaine_visite_medicale = models.DateField(null=True, blank=True, 
                                                 verbose_name="Prochaine visite médicale")
    aptitude_medicale = models.BooleanField(default=True, verbose_name="Apte médicalement")
    restrictions_medicales = models.TextField(blank=True, verbose_name="Restrictions médicales")
    
    # Documents RH
    documents_rh = models.JSONField(default=list, blank=True, verbose_name="Documents RH")
    
    # Évaluation
    dernier_entretien = models.DateField(null=True, blank=True, 
                                         verbose_name="Date du dernier entretien")
    prochain_entretien = models.DateField(null=True, blank=True, 
                                          verbose_name="Date du prochain entretien")
    evaluation_annuelle = models.DecimalField(max_digits=3, decimal_places=1, 
                                              null=True, blank=True, 
                                              verbose_name="Note évaluation annuelle")
    
    # Disponibilité
    disponible = models.BooleanField(default=True, verbose_name="Disponible")
    disponible_date_debut = models.DateField(null=True, blank=True, 
                                            verbose_name="Date de début de disponibilité")
    disponible_date_fin = models.DateField(null=True, blank=True, 
                                          verbose_name="Date de fin de disponibilité")
    
    # Agence principale (optionnel)
    agence_principale = models.ForeignKey(Agence, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='utilisateurs_principaux', 
                                          verbose_name="Agence principale")
    
    # Métadonnées
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dernière IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_users', verbose_name="Créé par")
    
    # Photo
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True, 
                                        verbose_name="Photo de profil")
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = "Utilisateur BTP"
        verbose_name_plural = "Utilisateurs BTP"
        permissions = [
            # Gestion globale
            ("can_view_reports", "Peut voir les rapports"),
            ("can_manage_users", "Peut gérer les utilisateurs"),
            ("can_validate_orders", "Peut valider les commandes"),
            ("can_manage_inventory", "Peut gérer l'inventaire"),
            ("can_manage_rh", "Peut gérer les ressources humaines"),
            ("can_view_all_agences", "Peut voir toutes les agences"),
            ("can_manage_accounting", "Peut gérer la comptabilité"),
            
            # Spécifique BTP
            ("can_manage_chantiers", "Peut gérer les chantiers"),
            ("can_validate_deviation", "Peut valider les déviations"),
            ("can_manage_engins", "Peut gérer le parc d'engins"),
            ("can_manage_sous_traitants", "Peut gérer les sous-traitants"),
            ("can_validate_safety", "Peut valider les documents sécurité"),
            ("can_manage_quality", "Peut gérer la qualité"),
            
            # Permissions RH
            ("can_manage_payroll", "Peut gérer la paie"),
            ("can_manage_recruitment", "Peut gérer le recrutement"),
            ("can_manage_training", "Peut gérer les formations"),
            ("can_manage_medical_visits", "Peut gérer les visites médicales"),
            ("can_view_employee_data", "Peut voir les données des employés"),
        ]

    def __str__(self):
        if self.est_pdg():
            return f"{self.get_full_name()} - PDG"
        roles = self.get_all_roles()
        role_str = ", ".join([r['role_display'] for r in roles[:3]])
        return f"{self.get_full_name()} - {role_str}"

    # ==================== MÉTHODES DE BASE ====================

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def get_full_name_display(self):
        return self.get_full_name()

    # ==================== MÉTHODE RÔLE GLOBAL ====================

    def est_pdg(self):
        return self.role_global == 'pdg'

    # ==================== MÉTHODES DE RÔLES PAR AGENCE ====================

    def est_directeur_agence(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'directeur_agence')
        return self.roles_agence.filter(role='directeur_agence', est_actif=True).exists()

    def est_chef_chantier(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'chef_chantier')
        return self.roles_agence.filter(role='chef_chantier', est_actif=True).exists()

    def est_conducteur_travaux(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'conducteur_travaux')
        return self.roles_agence.filter(role='conducteur_travaux', est_actif=True).exists()

    def est_technicien(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'technicien')
        return self.roles_agence.filter(role='technicien', est_actif=True).exists()

    def est_gestionnaire_stock(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'gestionnaire_stock')
        return self.roles_agence.filter(role='gestionnaire_stock', est_actif=True).exists()

    def est_commercial_btp(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'commercial_btp')
        return self.roles_agence.filter(role='commercial_btp', est_actif=True).exists()

    def est_comptable_btp(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'comptable_btp')
        return self.roles_agence.filter(role='comptable_btp', est_actif=True).exists()

    def est_responsable_qualite(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'responsable_qualite')
        return self.roles_agence.filter(role='responsable_qualite', est_actif=True).exists()

    def est_responsable_hse(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'responsable_hse')
        return self.roles_agence.filter(role='responsable_hse', est_actif=True).exists()

    def est_acheteur(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'acheteur')
        return self.roles_agence.filter(role='acheteur', est_actif=True).exists()

    def est_securite(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'securite')
        return self.roles_agence.filter(role='securite', est_actif=True).exists()

    def est_assistant_chantier(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'assistant_chantier')
        return self.roles_agence.filter(role='assistant_chantier', est_actif=True).exists()

    def est_assistant_admin(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'assistant_admin')
        return self.roles_agence.filter(role='assistant_admin', est_actif=True).exists()

    # ==================== MÉTHODES RH ====================

    def est_responsable_rh(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'responsable_rh')
        return self.roles_agence.filter(role='responsable_rh', est_actif=True).exists()

    def est_assistant_rh(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'assistant_rh')
        return self.roles_agence.filter(role='assistant_rh', est_actif=True).exists()

    def est_formateur(self, agence_id=None):
        if agence_id:
            return self.a_role_dans_agence(agence_id, 'formateur')
        return self.roles_agence.filter(role='formateur', est_actif=True).exists()

    def a_role_dans_agence(self, agence_id, role):
        if not agence_id:
            return self.roles_agence.filter(role=role, est_actif=True).exists()
        return self.roles_agence.filter(agence_id=agence_id, role=role, est_actif=True).exists()

    def get_role_dans_agence(self, agence_id):
        try:
            role_agence = self.roles_agence.get(agence_id=agence_id, est_actif=True)
            return role_agence.role
        except RoleAgence.DoesNotExist:
            return None

    def get_role_display_dans_agence(self, agence_id):
        role = self.get_role_dans_agence(agence_id)
        if role:
            return dict(RoleAgence.ROLE_CHOICES).get(role, role)
        return "Aucun rôle"

    # ==================== MÉTHODES D'ACCÈS AUX AGENCES ====================

    def get_agences(self):
        if self.est_pdg():
            return Agence.objects.filter(est_active=True)
        agences_ids = self.roles_agence.filter(est_actif=True).values_list('agence_id', flat=True)
        return Agence.objects.filter(id__in=agences_ids, est_active=True)

    def get_agences_par_type(self):
        agences = self.get_agences()
        return {
            'siege': agences.filter(type_agence='siege'),
            'regionale': agences.filter(type_agence='regionale'),
            'chantier': agences.filter(type_agence='chantier'),
            'logistique': agences.filter(type_agence='logistique'),
        }

    def get_agence_principale(self):
        if self.agence_principale:
            return self.agence_principale
        premiere_agence = self.roles_agence.filter(est_actif=True).first()
        if premiere_agence:
            return premiere_agence.agence
        return None

    def peut_acceder_agence(self, agence_id):
        if self.est_pdg():
            return True
        if not agence_id:
            return False
        return self.roles_agence.filter(agence_id=agence_id, est_actif=True).exists()

    # ==================== MÉTHODES DE GESTION DES RÔLES ====================

    def get_all_roles(self):
        roles = self.roles_agence.filter(est_actif=True).select_related('agence')
        return [
            {
                'agence_id': role.agence.id,
                'agence_nom': role.agence.nom,
                'agence_type': role.agence.type_agence,
                'role': role.role,
                'role_display': role.get_role_display(),
                'habilitations': role.habilitations,
                'certifications': role.certifications,
                'specialites': role.specialites,
            }
            for role in roles
        ]

    def get_roles_disponibles_agence(self, agence_id):
        try:
            agence = Agence.objects.get(id=agence_id)
            return agence.get_roles_disponibles()
        except Agence.DoesNotExist:
            return []

    def peut_assigner_role(self, agence_id, role):
        try:
            agence = Agence.objects.get(id=agence_id)
            roles_disponibles = [r[0] for r in agence.get_roles_disponibles()]
            return role in roles_disponibles
        except Agence.DoesNotExist:
            return False

    # ==================== MÉTHODES RH SPÉCIFIQUES ====================

    def a_habilitation(self, habilitation):
        return habilitation in self.habilitations

    def a_certification(self, certification):
        return certification in self.certifications

    def a_competence(self, competence):
        return competence in self.competences

    def est_apte_medicalement(self):
        return self.aptitude_medicale

    def est_disponible(self, date=None):
        if not self.disponible:
            return False
        if self.disponible_date_debut and self.disponible_date_fin:
            if not date:
                from datetime import date as date_today
                date = date_today.today()
            return self.disponible_date_debut <= date <= self.disponible_date_fin
        return True

    def get_anciennete(self):
        from datetime import date
        if not self.hire_date:
            return None
        today = date.today()
        return today.year - self.hire_date.year - ((today.month, today.day) < (self.hire_date.month, self.hire_date.day))

    def get_age(self):
        from datetime import date
        if not self.birthday:
            return None
        today = date.today()
        return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))

    # ==================== PERMISSIONS ====================

    def has_perm(self, perm, obj=None):
        if self.est_pdg():
            return True
        return super().has_perm(perm, obj)


# ==================== SIGNAL EMAIL ====================

@receiver(reset_password_token_created)
def password_reset_token_created(reset_password_token, *args, **kwargs):
    sitelink = "http://localhost:5173/"
    token = "{}".format(reset_password_token.key)
    full_link = str(sitelink) + str("password-reset/") + str(token)
    
    context = {
        'full_link': full_link,
        'email_address': reset_password_token.user.email
    }
    
    html_message = render_to_string("backend/email.html", context=context)
    plain_message = strip_tags(html_message)
    
    msg = EmailMultiAlternatives(
        subject=f"Réinitialisation de mot de passe pour {reset_password_token.user.email}",
        body=plain_message,
        from_email="codelivecamp@gmail.com",
        to=[reset_password_token.user.email]
    )
    
    msg.attach_alternative(html_message, "text/html")
    msg.send()