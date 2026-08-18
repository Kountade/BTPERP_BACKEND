from django.db import models

# Create your models here.
# crm/models.py
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Client(models.Model):
    """Client ou maître d'ouvrage"""
    
    TYPE_CHOICES = [
        ('particulier', 'Particulier'),
        ('entreprise', 'Entreprise'),
        ('collectivite', 'Collectivité'),
        ('promoteur', 'Promoteur'),
        ('bailleur', 'Bailleur social'),
    ]
    
    nom = models.CharField(max_length=200)
    type_client = models.CharField(max_length=20, choices=TYPE_CHOICES)
    siret = models.CharField(max_length=14, blank=True, null=True)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    adresse = models.TextField()
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=50, default='France')
    
    # Contact
    contact_principal = models.CharField(max_length=150)
    contact_telephone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    
    # Comptabilité
    numero_compte = models.CharField(max_length=20, blank=True, null=True)
    plafond_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Statut
    actif = models.BooleanField(default=True)
    note = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return self.nom


class Lead(models.Model):
    """Prospect ou opportunité commerciale"""
    
    STATUT_CHOICES = [
        ('nouveau', 'Nouveau'),
        ('contacte', 'Contacté'),
        ('qualifie', 'Qualifié'),
        ('devis', 'En devis'),
        ('perdu', 'Perdu'),
        ('gagne', 'Gagné'),
    ]
    
    SOURCE_CHOICES = [
        ('site_web', 'Site web'),
        ('bouche_a_oreille', 'Bouche à oreille'),
        ('publicite', 'Publicité'),
        ('salon', 'Salon professionnel'),
        ('appel', 'Appel d\'offres'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(max_length=200)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    societe = models.CharField(max_length=200, blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='nouveau')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    
    # Qualification
    type_travaux = models.CharField(max_length=200, blank=True)
    budget_estime = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    delai_souhaite = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    prochaine_action = models.DateField(null=True, blank=True)
    
    # Relations
    commercial = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leads')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_perte = models.DateField(null=True, blank=True)
    motif_perte = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.nom} - {self.get_statut_display()}"


class Interaction(models.Model):
    """Historique des interactions avec un lead/client"""
    
    TYPE_CHOICES = [
        ('appel', 'Appel téléphonique'),
        ('email', 'Email'),
        ('rencontre', 'Rencontre'),
        ('visite_chantier', 'Visite de chantier'),
        ('reunion', 'Réunion'),
        ('autre', 'Autre'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='interactions')
    projet = models.ForeignKey('chantiers.Projet', on_delete=models.SET_NULL, null=True, blank=True)
    
    type_interaction = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date = models.DateTimeField(auto_now_add=True)
    duree = models.IntegerField(help_text="Durée en minutes", blank=True, null=True)
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_type_interaction_display()} - {self.lead or self.client}"


class AppelOffre(models.Model):
    """Appel d'offres reçu"""
    
    STATUT_CHOICES = [
        ('recu', 'Reçu'),
        ('en_cours', 'En cours'),
        ('soumis', 'Soumis'),
        ('gagne', 'Gagné'),
        ('perdu', 'Perdu'),
    ]
    
    reference = models.CharField(max_length=50)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='appels_offres')
    
    objet = models.CharField(max_length=200)
    description = models.TextField()
    date_publication = models.DateField()
    date_limite = models.DateField()
    date_soumission = models.DateField(null=True, blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='recu')
    budget_estime = models.DecimalField(max_digits=12, decimal_places=2)
    montant_soumis = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    documents = models.FileField(upload_to='appels_offres/%Y/%m/', blank=True)
    notes = models.TextField(blank=True)
    
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='appels_offres')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"AO {self.reference} - {self.client.nom}"