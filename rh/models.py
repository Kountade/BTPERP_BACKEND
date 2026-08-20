# rh/models.py - Version avec 10 champs pour Employé et 10 champs pour Contrat

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class Service(models.Model):
    """Service ou département"""
    
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    responsable = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_responsable')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.nom


class Poste(models.Model):
    """Poste ou métier"""
    
    CATEGORIE_CHOICES = [
        ('direction', 'Direction'),
        ('maitrise', 'Maîtrise'),
        ('technicien', 'Technicien'),
        ('ouvrier', 'Ouvrier'),
        ('administratif', 'Administratif'),
    ]
    
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, unique=True)
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    niveau = models.CharField(max_length=50)
    coefficient = models.IntegerField()
    
    # Compétences requises
    competences_requises = models.ManyToManyField('Competence', blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.nom}"


# ✅ TABLE EMPLOYE - 10 CHAMPS EXACTEMENT
class Employe(models.Model):
    """Employé de l'entreprise - 10 champs"""
    
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    # === 10 CHAMPS ===
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)  # 1
    matricule = models.CharField(max_length=20, unique=True)  # 2
    nom = models.CharField(max_length=100)  # 3
    prenom = models.CharField(max_length=100)  # 4
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)  # 5
    email = models.EmailField(unique=True)  # 6
    telephone = models.CharField(max_length=20)  # 7
    adresse = models.TextField()  # 8
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT, related_name='employes')  # 9
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='employes')  # 10
    
    # Métadonnées (non comptées dans les 10 champs)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.matricule} - {self.nom} {self.prenom}"
    
    @property
    def full_name(self):
        return f"{self.nom} {self.prenom}"


# ✅ TABLE CONTRAT - 10 CHAMPS EXACTEMENT
class Contrat(models.Model):
    """Contrat de travail d'un employé - 10 champs"""
    
    SITUATION_CHOICES = [
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('interim', 'Intérim'),
        ('apprenti', 'Apprenti'),
        ('stagiaire', 'Stagiaire'),
        ('auto_entrepreneur', 'Auto-Entrepreneur'),
    ]
    
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('termine', 'Terminé'),
        ('resilie', 'Résilié'),
        ('suspendu', 'Suspendu'),
    ]
    
    # === 10 CHAMPS ===
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='contrats')  # 1
    situation = models.CharField(max_length=20, choices=SITUATION_CHOICES)  # 2
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')  # 3
    date_embauche = models.DateField()  # 4
    date_fin_contrat = models.DateField(null=True, blank=True)  # 5
    salaire_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 6
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 7
    prime_panier = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 8
    indemnite_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 9
    prime_anciennete = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 10
    
    # Métadonnées (non comptées dans les 10 champs)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_embauche']
    
    def __str__(self):
        return f"{self.employe.nom} - {self.get_situation_display()} - {self.date_embauche}"
    
    @property
    def anciennete(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_embauche.year
    
    @property
    def est_actif(self):
        return self.statut == 'actif'


# ✅ CLASSES RH EXISTANTES (inchangées)
class Competence(models.Model):
    """Compétence d'un employé"""
    
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
        ('expert', 'Expert'),
    ]
    
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.nom


class EmployeCompetence(models.Model):
    """Compétence d'un employé spécifique"""
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='competences')
    competence = models.ForeignKey(Competence, on_delete=models.CASCADE)
    niveau = models.CharField(max_length=20, choices=Competence.NIVEAU_CHOICES)
    date_obtention = models.DateField()
    date_expiration = models.DateField(null=True, blank=True)
    valide = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('employe', 'competence')


class Formation(models.Model):
    """Formation suivie par un employé"""
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='formations')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='formations')
    nom = models.CharField(max_length=200)
    organisme = models.CharField(max_length=200)
    date_debut = models.DateField()
    date_fin = models.DateField()
    duree_heures = models.IntegerField()
    cout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    certificat = models.CharField(max_length=100, blank=True)
    valide = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.employe.nom} - {self.nom}"


class Pointage(models.Model):
    """Pointage des heures de travail"""
    
    TYPE_CHOICES = [
        ('arrivee', 'Arrivée'),
        ('depart', 'Départ'),
        ('pause', 'Pause'),
        ('retour_pause', 'Retour de pause'),
        ('heure_sup', 'Heure supplémentaire'),
    ]
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='pointages')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='pointages')
    projet = models.ForeignKey('chantiers.Projet', on_delete=models.SET_NULL, null=True, blank=True)
    tache = models.ForeignKey('chantiers.Tache', on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField(auto_now_add=True)
    heure = models.TimeField(auto_now_add=True)
    type_pointage = models.CharField(max_length=20, choices=TYPE_CHOICES)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    remarque = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.employe.nom} - {self.get_type_pointage_display()} - {self.date}"


class HeureTravail(models.Model):
    """Récapitulatif des heures travaillées par jour"""
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='heures_travail')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='heures_travail')
    projet = models.ForeignKey('chantiers.Projet', on_delete=models.SET_NULL, null=True, blank=True)
    tache = models.ForeignKey('chantiers.Tache', on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField()
    heures_normales = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_supplementaires = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_nuit = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heures_weekend = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    valide = models.BooleanField(default=False)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('employe', 'date')


class Absence(models.Model):
    """Absence d'un employé"""
    
    TYPE_CHOICES = [
        ('cp', 'Congés payés'),
        ('rtt', 'RTT'),
        ('maladie', 'Maladie'),
        ('accident', 'Accident du travail'),
        ('maternite', 'Maternité'),
        ('sans_solde', 'Sans solde'),
        ('formation', 'Formation'),
        ('autre', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('demandee', 'Demandée'),
        ('approuvee', 'Approuvée'),
        ('refusee', 'Refusée'),
        ('annulee', 'Annulée'),
    ]
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='absences')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='absences')
    type_absence = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    nombre_jours = models.IntegerField(editable=False)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='demandee')
    motif = models.TextField(blank=True)
    justificatif = models.FileField(upload_to='justificatifs/%Y/%m/', blank=True)
    
    approuve_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        delta = self.date_fin - self.date_debut
        self.nombre_jours = delta.days + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employe.nom} - {self.get_type_absence_display()} - {self.date_debut}"


class NoteDeFrais(models.Model):
    """Note de frais d'un employé"""
    
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('soumise', 'Soumise'),
        ('approuvee', 'Approuvée'),
        ('refusee', 'Refusée'),
    ]
    
    TYPE_CHOICES = [
        ('peage', 'Péage'),
        ('carburant', 'Carburant'),
        ('repas', 'Repas'),
        ('hebergement', 'Hébergement'),
        ('transport', 'Transport'),
        ('materiel', 'Petit matériel'),
        ('autre', 'Autre'),
    ]
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='notes_frais')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes_frais')
    projet = models.ForeignKey('chantiers.Projet', on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField()
    type_frais = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    justificatif = models.FileField(upload_to='notes_frais/%Y/%m/', blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    date_soumission = models.DateTimeField(null=True, blank=True)
    date_approbation = models.DateTimeField(null=True, blank=True)
    
    approuve_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employe.nom} - {self.get_type_frais_display()} - {self.montant}€"


class PlanningEmploye(models.Model):
    """Planning d'un employé sur un chantier"""
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='plannings')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='plannings')
    projet = models.ForeignKey('chantiers.Projet', on_delete=models.CASCADE, related_name='plannings_employes')
    tache = models.ForeignKey('chantiers.Tache', on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_heures = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    
    notes = models.TextField(blank=True)
    valide = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        from datetime import datetime
        debut = datetime.combine(self.date, self.heure_debut)
        fin = datetime.combine(self.date, self.heure_fin)
        self.duree_heures = (fin - debut).seconds / 3600
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['date', 'heure_debut']


# rh/models.py - Version corrigée avec la méthode generate_unique_number

import random
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# ... (autres modèles inchangés: Service, Poste, Employe, Contrat, Competence, etc.)


# ✅ TABLE DPAE CORRIGÉE AVEC MÉTHODE
class DPAE(models.Model):
    """Déclaration Préalable à l'Embauche"""
    
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='dpaes')
    contrat = models.ForeignKey(Contrat, on_delete=models.SET_NULL, null=True, blank=True, related_name='dpaes')
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True)  # ✅ AUTO-GÉNÉRÉ
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_embauche = models.DateField()
    date_fin_contrat = models.DateField(null=True, blank=True)
    motif_embauche = models.CharField(max_length=200)
    transmis = models.BooleanField(default=False)
    numero_ursaff = models.CharField(max_length=20, blank=True)
    
    def save(self, *args, **kwargs):
        # ✅ Générer un numéro automatiquement si vide
        if not self.numero:
            self.numero = self.generate_unique_number()
        super().save(*args, **kwargs)
    
    def generate_unique_number(self):
        """Génère un numéro unique pour la DPAE"""
        
        # Récupérer le dernier numéro
        last = DPAE.objects.all().order_by('-id').first()
        
        if last and last.numero:
            try:
                num = int(last.numero) + 1
                new_num = str(num).zfill(6)
            except (ValueError, TypeError):
                new_num = str(random.randint(100000, 999999))
        else:
            new_num = '000001'
        
        # ✅ Vérifier l'unicité
        counter = 0
        while DPAE.objects.filter(numero=new_num).exists() and counter < 100:
            try:
                num = int(new_num) + 1
                new_num = str(num).zfill(6)
            except (ValueError, TypeError):
                new_num = str(random.randint(100000, 999999))
            counter += 1
        
        # Si toujours pas unique, ajouter un timestamp
        if DPAE.objects.filter(numero=new_num).exists():
            new_num = f"DPAE_{int(random.random() * 1000000)}"
        
        return new_num
    
    def __str__(self):
        return f"DPAE {self.numero or 'Sans numéro'} - {self.employe.nom}"