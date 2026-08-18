from django.db import models

# Create your models here.
# chantiers/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class Projet(models.Model):
    """Projet ou chantier principal"""
    
    STATUT_CHOICES = [
        ('etude', 'En étude'),
        ('encours', 'En cours'),
        ('suspendu', 'Suspendu'),
        ('termine', 'Terminé'),
        ('livre', 'Livré'),
    ]
    
    TYPE_CHOICES = [
        ('construction', 'Construction neuve'),
        ('renovation', 'Rénovation'),
        ('extension', 'Extension'),
        ('tp', 'Travaux Publics'),
        ('entretien', 'Entretien'),
        ('demolition', 'Démolition'),
    ]
    
    # Identité
    code = models.CharField(max_length=20, unique=True, verbose_name="Code chantier")
    nom = models.CharField(max_length=200, verbose_name="Nom du projet")
    type_projet = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='etude', verbose_name="Statut")
    
    # Relations
    client = models.ForeignKey('crm.Client', on_delete=models.PROTECT, related_name='projets', verbose_name="Client")
    chef_projet = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='projets_chef', verbose_name="Chef de projet")
    agence = models.ForeignKey('users.Agence', on_delete=models.SET_NULL, null=True, related_name='projets', verbose_name="Agence")
    
    # Dates
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin_previsionnelle = models.DateField(verbose_name="Date de fin prévisionnelle")
    date_fin_reelle = models.DateField(null=True, blank=True, verbose_name="Date de fin réelle")
    duree_jours = models.IntegerField(editable=False, null=True, blank=True)
    
    # Budget
    budget_total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Budget total")
    budget_mo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Budget Main d'œuvre")
    budget_materiaux = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Budget Matériaux")
    budget_sous_traitance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Budget Sous-traitance")
    budget_frais_generaux = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Budget Frais généraux")
    
    # Coûts réels (mis à jour automatiquement)
    cout_reel_mo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Coût réel MO")
    cout_reel_materiaux = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Coût réel Matériaux")
    cout_reel_sous_traitance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Coût réel Sous-traitance")
    cout_reel_frais_generaux = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Coût réel Frais généraux")
    
    # Localisation
    adresse_chantier = models.TextField(verbose_name="Adresse du chantier")
    code_postal = models.CharField(max_length=10, verbose_name="Code postal")
    ville = models.CharField(max_length=100, verbose_name="Ville")
    coordonnees_gps = models.CharField(max_length=100, blank=True, null=True, verbose_name="Coordonnées GPS")
    
    # Indicateurs
    taux_avancement = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Taux d'avancement (%)")
    rentabilite_previsionnelle = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Rentabilité prévisionnelle (%)")
    note_qualite = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name="Note qualité")
    niveau_risque = models.CharField(max_length=10, default='Faible', verbose_name="Niveau de risque")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='projets_crees')
    
    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Projet"
        verbose_name_plural = "Projets"
        permissions = [
            ("can_manage_projets", "Peut gérer les projets"),
            ("can_view_all_projets", "Peut voir tous les projets"),
            ("can_validate_budget", "Peut valider les budgets"),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.nom}"
    
    def get_cout_total(self):
        """Retourne le coût total réel"""
        return (self.cout_reel_mo + self.cout_reel_materiaux + 
                self.cout_reel_sous_traitance + self.cout_reel_frais_generaux)
    
    def get_marge_reelle(self):
        """Retourne la marge réelle"""
        ca = self.get_chiffre_affaires()
        cout = self.get_cout_total()
        return ca - cout
    
    def get_chiffre_affaires(self):
        """Retourne le chiffre d'affaires du projet"""
        from finance.models import Facture
        return Facture.objects.filter(projet=self, statut='payee').aggregate(
            total=models.Sum('montant_ttc'))['total'] or Decimal('0')


class Phase(models.Model):
    """Phase ou lot de travaux"""
    
    TYPE_CHOICES = [
        ('vrd', 'Voirie Réseaux Divers'),
        ('gros_oeuvre', 'Gros œuvre'),
        ('second_oeuvre', 'Second œuvre'),
        ('finitions', 'Finitions'),
        ('amenagement', 'Aménagement extérieur'),
        ('terrassement', 'Terrassement'),
        ('fondation', 'Fondation'),
    ]
    
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='phases')
    nom = models.CharField(max_length=200)
    type_phase = models.CharField(max_length=20, choices=TYPE_CHOICES)
    ordre = models.IntegerField()
    
    # Dates
    date_debut = models.DateField()
    date_fin_previsionnelle = models.DateField()
    date_fin_reelle = models.DateField(null=True, blank=True)
    
    # Budget
    budget = models.DecimalField(max_digits=15, decimal_places=2)
    cout_reel = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Suivi
    taux_avancement = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='phases_responsable')
    
    class Meta:
        ordering = ['ordre']
    
    def __str__(self):
        return f"{self.projet.code} - {self.nom}"


class Tache(models.Model):
    """Tâche opérationnelle sur le chantier"""
    
    PRIORITE_CHOICES = [
        ('critique', 'Critique'),
        ('haute', 'Haute'),
        ('moyenne', 'Moyenne'),
        ('basse', 'Basse'),
    ]
    
    STATUT_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('blocage', 'En blocage'),
        ('a_valider', 'À valider'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='taches')
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priorite = models.CharField(max_length=20, choices=PRIORITE_CHOICES, default='moyenne')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='a_faire')
    
    # Dates
    date_debut = models.DateTimeField()
    date_fin_previsionnelle = models.DateTimeField()
    date_fin_reelle = models.DateTimeField(null=True, blank=True)
    duree_estimee = models.FloatField(help_text="Temps estimé en heures")
    
    # Ressources
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='taches_responsable')
    equipe = models.ManyToManyField('rh.Employe', through='AffectationTache', blank=True)
    
    # Dépendances
    dependances = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    # Coûts
    cout_estime = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cout_reel = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.phase.projet.code} - {self.nom}"


class AffectationTache(models.Model):
    """Affectation d'un employé à une tâche"""
    
    tache = models.ForeignKey(Tache, on_delete=models.CASCADE)
    employe = models.ForeignKey('rh.Employe', on_delete=models.CASCADE)
    heures_prevues = models.FloatField(default=0)
    heures_reelles = models.FloatField(default=0)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=100, default='Ouvrier')
    
    class Meta:
        unique_together = ('tache', 'employe')


class SousTraitant(models.Model):
    """Sous-traitant intervenant sur le chantier"""
    
    ENTREPRISE_TYPES = [
        ('tp', 'Travaux Publics'),
        ('gros_oeuvre', 'Gros œuvre'),
        ('second_oeuvre', 'Second œuvre'),
        ('electricite', 'Électricité'),
        ('plomberie', 'Plomberie'),
        ('climatisation', 'Climatisation'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(max_length=200)
    siret = models.CharField(max_length=14, unique=True)
    type_entreprise = models.CharField(max_length=20, choices=ENTREPRISE_TYPES)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    
    # Responsable
    contact_nom = models.CharField(max_length=150)
    contact_telephone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    
    # Qualité
    note = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    actif = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom


class InterventionSousTraitant(models.Model):
    """Intervention d'un sous-traitant sur un chantier"""
    
    STATUT_CHOICES = [
        ('planifie', 'Planifiée'),
        ('encours', 'En cours'),
        ('termine', 'Terminée'),
        ('annule', 'Annulée'),
    ]
    
    sous_traitant = models.ForeignKey(SousTraitant, on_delete=models.PROTECT, related_name='interventions')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='interventions_st')
    phase = models.ForeignKey(Phase, on_delete=models.SET_NULL, null=True, blank=True)
    
    description = models.TextField()
    montant_estime = models.DecimalField(max_digits=12, decimal_places=2)
    montant_reel = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifie')
    
    # Documents
    bon_commande = models.CharField(max_length=50, blank=True)
    facture = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sous_traitant.nom} - {self.projet.code}"


class DocumentChantier(models.Model):
    """Documents liés au chantier"""
    
    TYPE_CHOICES = [
        ('plan', 'Plan'),
        ('rapport', 'Rapport'),
        ('photo', 'Photographie'),
        ('courrier', 'Courrier'),
        ('certificat', 'Certificat'),
        ('pv', 'Procès-verbal'),
        ('rfi', 'Demande d\'information'),
        ('autre', 'Autre'),
    ]
    
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='documents')
    type_document = models.CharField(max_length=20, choices=TYPE_CHOICES)
    nom = models.CharField(max_length=200)
    fichier = models.FileField(upload_to='documents_chantier/%Y/%m/')
    version = models.CharField(max_length=20, default='1.0')
    description = models.TextField(blank=True)
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_upload = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.projet.code} - {self.nom}"


class RapportQuotidien(models.Model):
    """Rapport journalier de chantier"""
    
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='rapports_quotidiens')
    date = models.DateField()
    redacteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Sections
    conditions_meteo = models.TextField(blank=True)
    effectif_present = models.IntegerField()
    travaux_realises = models.TextField()
    travaux_prevus = models.TextField()
    difficultes = models.TextField(blank=True)
    securite = models.TextField(blank=True)
    materiel_utilise = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    
    # Signatures
    signe_chef_chantier = models.BooleanField(default=False)
    signe_client = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('projet', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"Rapport {self.projet.code} - {self.date}"