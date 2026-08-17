# users/permissions.py
"""
Permissions personnalisées pour l'application users
Gestion des accès basés sur les rôles BTP et les agences
"""

from rest_framework.permissions import BasePermission


class HasAgenceAccess(BasePermission):
    """
    Permission pour vérifier que l'utilisateur a accès à l'agence
    - PDG a accès à tout
    - Les autres utilisateurs n'ont accès qu'à leurs agences
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        # Vérifier si l'objet a un champ 'agence'
        if hasattr(obj, 'agence') and obj.agence:
            return request.user.peut_acceder_agence(obj.agence.id)

        # Si l'objet est une agence directement
        if hasattr(obj, 'est_active'):
            return request.user.peut_acceder_agence(obj.id)

        return False


class IsPDG(BasePermission):
    """Permission pour les PDG uniquement"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'est_pdg') and request.user.est_pdg()


class IsPDGOrDRH(BasePermission):
    """Permission pour les PDG ou DRH (conservé pour compatibilité)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (hasattr(request.user, 'est_pdg') and request.user.est_pdg())


# ==================== RÔLES PAR AGENCE BTP ====================

class IsDirecteurAgence(BasePermission):
    """Permission pour les Directeurs d'Agence (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_directeur_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if request.user.est_directeur_agence(agence.id):
                    return True

        return False


class IsChefChantier(BasePermission):
    """Permission pour les Chefs de Chantier (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_directeur_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_chef_chantier(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsConducteurTravaux(BasePermission):
    """Permission pour les Conducteurs de Travaux (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_conducteur_travaux'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_conducteur_travaux(agence.id) or 
                    request.user.est_chef_chantier(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsGestionnaireStock(BasePermission):
    """Permission pour les Gestionnaires de Stock (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_gestionnaire_stock'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_gestionnaire_stock(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsCommercialBTP(BasePermission):
    """Permission pour les Commerciaux BTP (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_commercial_btp'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_commercial_btp(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsComptableBTP(BasePermission):
    """Permission pour les Comptables BTP (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_comptable_btp'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_comptable_btp(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsResponsableHSE(BasePermission):
    """Permission pour les Responsables HSE (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_responsable_hse'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_responsable_hse(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsAcheteur(BasePermission):
    """Permission pour les Acheteurs (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_acheteur'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_acheteur(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsResponsableQualite(BasePermission):
    """Permission pour les Responsables Qualité (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_responsable_qualite'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_responsable_qualite(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


# ==================== RÔLES RH ====================

class IsResponsableRH(BasePermission):
    """Permission pour les Responsables RH (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_responsable_rh'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_responsable_rh(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsAssistantRH(BasePermission):
    """Permission pour les Assistants RH (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_assistant_rh'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_assistant_rh(agence.id) or 
                    request.user.est_responsable_rh(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


class IsFormateur(BasePermission):
    """Permission pour les Formateurs (ou supérieur)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'est_formateur'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.est_formateur(agence.id) or 
                    request.user.est_responsable_rh(agence.id) or 
                    request.user.est_directeur_agence(agence.id)):
                    return True

        return False


# ==================== PERMISSIONS COMBINÉES ====================

class IsPersonnelAgence(BasePermission):
    """
    Permission pour tout le personnel d'agence
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                roles = ['directeur_agence', 'chef_chantier', 'conducteur_travaux',
                        'gestionnaire_stock', 'commercial_btp', 'comptable_btp',
                        'responsable_qualite', 'responsable_hse', 'acheteur',
                        'responsable_rh', 'assistant_rh', 'formateur',
                        'technicien', 'securite', 'assistant_chantier', 'assistant_admin']
                for role in roles:
                    if request.user.a_role_dans_agence(agence.id, role):
                        return True

        return False


class IsGestionnaireOuComptable(BasePermission):
    """Permission pour les Gestionnaires de Stock ou Comptables"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'gestionnaire_stock') or 
                    request.user.a_role_dans_agence(agence.id, 'comptable_btp') or
                    request.user.a_role_dans_agence(agence.id, 'directeur_agence')):
                    return True

        return False


# ==================== PERMISSIONS SPÉCIFIQUES ====================

class CanManageInventory(BasePermission):
    """Permission pour la gestion d'inventaire"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('inventory.can_manage_inventory'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'gestionnaire_stock') or 
                    request.user.a_role_dans_agence(agence.id, 'directeur_agence') or
                    request.user.a_role_dans_agence(agence.id, 'chef_chantier')):
                    return True

        return False


class CanManageAccounting(BasePermission):
    """Permission pour la gestion comptable"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('users.can_manage_accounting'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'comptable_btp') or 
                    request.user.a_role_dans_agence(agence.id, 'directeur_agence')):
                    return True

        return False


class CanManageUsers(BasePermission):
    """Permission pour gérer les utilisateurs (RH)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('users.can_manage_users'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'responsable_rh') or 
                    request.user.a_role_dans_agence(agence.id, 'directeur_agence')):
                    return True

        return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if hasattr(obj, 'roles_agence'):
            user_agences = obj.roles_agence.filter(
                est_actif=True).values_list('agence_id', flat=True)
            current_agences = request.user.get_agences().values_list('id', flat=True)
            return bool(set(user_agences) & set(current_agences))

        return False


class CanViewReports(BasePermission):
    """Permission pour voir les rapports et analyses"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('users.can_view_reports'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                roles = ['directeur_agence', 'chef_chantier', 'conducteur_travaux',
                        'comptable_btp', 'responsable_rh', 'gestionnaire_stock']
                for role in roles:
                    if request.user.a_role_dans_agence(agence.id, role):
                        return True

        return False


class CanManageRH(BasePermission):
    """Permission pour la gestion des Ressources Humaines"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('users.can_manage_rh'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'responsable_rh') or 
                    request.user.a_role_dans_agence(agence.id, 'directeur_agence')):
                    return True

        return False


class CanManageChantiers(BasePermission):
    """Permission pour la gestion des chantiers"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'est_pdg') and request.user.est_pdg():
            return True

        if request.user.has_perm('users.can_manage_chantiers'):
            return True

        if hasattr(request.user, 'a_role_dans_agence'):
            agences = request.user.get_agences()
            for agence in agences:
                if (request.user.a_role_dans_agence(agence.id, 'directeur_agence') or 
                    request.user.a_role_dans_agence(agence.id, 'chef_chantier') or
                    request.user.a_role_dans_agence(agence.id, 'conducteur_travaux')):
                    return True

        return False