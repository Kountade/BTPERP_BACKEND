# users/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from knox.models import AuthToken
from rest_framework.decorators import action
from django.db.models import Q
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserDetailSerializer,
    AgenceSerializer,
    AgenceCreateSerializer,
    AgenceSimpleSerializer,
    RoleAgenceSerializer,
    AssignRoleSerializer
)
from .models import Agence, RoleAgence, CustomUser
from .permissions import *

User = get_user_model()


class LoginViewset(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, email=email, password=password)
            if user:
                if not user.is_active:
                    return Response({"error": "Compte désactivé"}, status=401)
                _, token = AuthToken.objects.create(user)
                user_data = UserSerializer(user).data
                return Response({"user": user_data, "token": token})
            return Response({"error": "Email ou mot de passe incorrect"}, status=401)
        return Response(serializer.errors, status=400)


class RegisterViewset(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)


class UserViewset(viewsets.ViewSet):
    """
    ViewSet pour la gestion des utilisateurs BTP
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.est_pdg():
            return User.objects.all()
        agences_ids = user.roles_agence.filter(
            est_actif=True).values_list('agence_id', flat=True)
        return User.objects.filter(
            Q(roles_agence__agence_id__in=agences_ids,
              roles_agence__est_actif=True) | Q(id=user.id)
        ).distinct()

    def list(self, request):
        queryset = self.get_queryset()
        role_global = request.query_params.get('role_global')
        if role_global:
            queryset = queryset.filter(role_global=role_global)
        agence_id = request.query_params.get('agence_id')
        if agence_id:
            queryset = queryset.filter(
                roles_agence__agence_id=agence_id, roles_agence__est_actif=True)
        role_type = request.query_params.get('role_type')
        if role_type:
            queryset = queryset.filter(
                roles_agence__role=role_type, roles_agence__est_actif=True)
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            if not request.user.est_pdg():
                if request.user.id != user.id:
                    user_agences = user.roles_agence.filter(
                        est_actif=True).values_list('agence_id', flat=True)
                    current_agences = request.user.roles_agence.filter(
                        est_actif=True).values_list('agence_id', flat=True)
                    if not set(user_agences) & set(current_agences):
                        return Response({"error": "Permission denied"}, status=403)
            serializer = UserDetailSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)

    def create(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        if not request.user.est_pdg():
            if request.user.id != int(pk):
                return Response({"error": "Permission denied"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        serializer = UserDetailSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        if not request.user.est_pdg():
            if request.user.id != int(pk):
                return Response({"error": "Permission denied"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        serializer = UserDetailSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut supprimer des utilisateurs"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        if request.user.id == user.id:
            return Response({"error": "Vous ne pouvez pas supprimer votre propre compte"}, status=400)
        user.delete()
        return Response({"message": "Utilisateur supprimé avec succès"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut modifier le statut des utilisateurs"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        if request.user.id == user.id and user.is_active:
            return Response({"error": "Vous ne pouvez pas désactiver votre propre compte"}, status=400)
        user.is_active = not user.is_active
        user.save()
        status_text = "activé" if user.is_active else "désactivé"
        return Response({
            "id": user.id,
            "is_active": user.is_active,
            "message": f"Utilisateur {user.email} {status_text} avec succès"
        })

    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut assigner des rôles"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        serializer = AssignRoleSerializer(data=request.data)
        if serializer.is_valid():
            role = RoleAgence.objects.create(
                user=user,
                agence_id=serializer.validated_data['agence_id'],
                role=serializer.validated_data['role'],
                est_actif=True
            )
            return Response(RoleAgenceSerializer(role).data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['delete'])
    def remove_role(self, request, pk=None):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut retirer des rôles"}, status=403)
        role_id = request.data.get('role_id')
        if not role_id:
            return Response({"error": "role_id required"}, status=400)
        try:
            role = RoleAgence.objects.get(id=role_id, user_id=pk)
            role.est_actif = False
            role.save()
            return Response({"message": "Rôle retiré avec succès"})
        except RoleAgence.DoesNotExist:
            return Response({"error": "Rôle non trouvé"}, status=404)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        if not request.user.est_pdg():
            return Response({"error": "Permission denied"}, status=403)
        users = self.get_queryset()
        stats = {
            "total": users.count(),
            "active": users.filter(is_active=True).count(),
            "inactive": users.filter(is_active=False).count(),
            "pdg": users.filter(role_global='pdg').count(),
            "autre": users.filter(role_global='autre').count(),
            "by_agence": {},
            "by_role": {
                "directeur_agence": RoleAgence.objects.filter(role='directeur_agence', est_actif=True).count(),
                "chef_chantier": RoleAgence.objects.filter(role='chef_chantier', est_actif=True).count(),
                "conducteur_travaux": RoleAgence.objects.filter(role='conducteur_travaux', est_actif=True).count(),
                "gestionnaire_stock": RoleAgence.objects.filter(role='gestionnaire_stock', est_actif=True).count(),
                "commercial_btp": RoleAgence.objects.filter(role='commercial_btp', est_actif=True).count(),
                "comptable_btp": RoleAgence.objects.filter(role='comptable_btp', est_actif=True).count(),
                "responsable_hse": RoleAgence.objects.filter(role='responsable_hse', est_actif=True).count(),
                "responsable_rh": RoleAgence.objects.filter(role='responsable_rh', est_actif=True).count(),
            }
        }
        for agence in Agence.objects.filter(est_active=True):
            count = users.filter(roles_agence__agence_id=agence.id, roles_agence__est_actif=True).count()
            if count > 0:
                stats["by_agence"][agence.nom] = {
                    "total": count,
                    "directeurs": agence.roles.filter(role='directeur_agence', est_actif=True).count(),
                    "chefs_chantier": agence.roles.filter(role='chef_chantier', est_actif=True).count(),
                    "conducteurs": agence.roles.filter(role='conducteur_travaux', est_actif=True).count(),
                    "gestionnaires": agence.roles.filter(role='gestionnaire_stock', est_actif=True).count(),
                    "commerciaux": agence.roles.filter(role='commercial_btp', est_actif=True).count(),
                    "comptables": agence.roles.filter(role='comptable_btp', est_actif=True).count(),
                    "hse": agence.roles.filter(role='responsable_hse', est_actif=True).count(),
                    "rh": agence.roles.filter(role='responsable_rh', est_actif=True).count(),
                }
        return Response(stats)

    @action(detail=False, methods=['get'])
    def by_role(self, request):
        role_type = request.query_params.get('role')
        if not role_type:
            return Response({"error": "Paramètre 'role' requis"}, status=400)
        roles_disponibles = [r[0] for r in RoleAgence.ROLE_CHOICES]
        if role_type not in roles_disponibles:
            return Response({"error": f"Rôle '{role_type}' invalide"}, status=400)
        users = User.objects.filter(
            roles_agence__role=role_type,
            roles_agence__est_actif=True,
            is_active=True
        ).distinct()
        if not request.user.est_pdg():
            agences_ids = request.user.roles_agence.filter(
                est_actif=True).values_list('agence_id', flat=True)
            users = users.filter(roles_agence__agence_id__in=agences_ids)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ProfileViewset(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDetailSerializer

    def retrieve(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    def update(self, request):
        serializer = self.serializer_class(
            request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'])
    def agences(self, request):
        agences = request.user.get_agences()
        serializer = AgenceSerializer(agences, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def roles(self, request):
        roles = request.user.roles_agence.filter(est_actif=True).select_related('agence')
        return Response([
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
        ])


class AgenceViewset(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgenceSerializer

    def get_queryset(self):
        user = self.request.user
        if self.action == 'list':
            return Agence.objects.filter(est_active=True)
        if user.est_pdg():
            return Agence.objects.all()
        else:
            agences_ids = user.roles_agence.filter(
                est_actif=True).values_list('agence_id', flat=True)
            return Agence.objects.filter(id__in=agences_ids, est_active=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return AgenceCreateSerializer
        return AgenceSerializer

    def create(self, request, *args, **kwargs):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut créer des agences"}, status=403)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            agence = serializer.save(created_by=request.user)
            return Response(AgenceSerializer(agence).data, status=201)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut modifier une agence"}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut supprimer une agence"}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def utilisateurs(self, request, pk=None):
        agence = self.get_object()
        if not (request.user.est_pdg() or request.user.peut_acceder_agence(agence.id)):
            return Response({"error": "Permission denied"}, status=403)
        role_filter = request.query_params.get('role')
        roles = agence.roles.filter(est_actif=True).select_related('user')
        if role_filter:
            roles = roles.filter(role=role_filter)
        utilisateurs = [{
            'user': UserSerializer(r.user).data,
            'role': r.role,
            'role_display': r.get_role_display(),
            'date_attribution': r.date_attribution,
            'est_actif': r.est_actif,
            'habilitations': r.habilitations,
            'certifications': r.certifications,
            'specialites': r.specialites,
        } for r in roles]
        return Response(utilisateurs)

    @action(detail=True, methods=['get'])
    def roles_disponibles(self, request, pk=None):
        agence = self.get_object()
        if not request.user.est_pdg():
            return Response({"error": "Permission denied"}, status=403)
        roles = [{'value': r[0], 'label': r[1]}
                 for r in agence.get_roles_disponibles()]
        return Response({
            'type_agence': agence.type_agence,
            'type_display': agence.get_type_agence_display(),
            'roles': roles
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        agence = self.get_object()
        if not (request.user.est_pdg() or request.user.peut_acceder_agence(agence.id)):
            return Response({"error": "Permission denied"}, status=403)
        roles = agence.roles.filter(est_actif=True)
        stats = {
            'agence_id': agence.id,
            'agence_nom': agence.nom,
            'type_agence': agence.type_agence,
            'total_utilisateurs': roles.count(),
            'par_role': {
                'directeur_agence': roles.filter(role='directeur_agence').count(),
                'chef_chantier': roles.filter(role='chef_chantier').count(),
                'conducteur_travaux': roles.filter(role='conducteur_travaux').count(),
                'gestionnaire_stock': roles.filter(role='gestionnaire_stock').count(),
                'commercial_btp': roles.filter(role='commercial_btp').count(),
                'comptable_btp': roles.filter(role='comptable_btp').count(),
                'responsable_hse': roles.filter(role='responsable_hse').count(),
                'responsable_rh': roles.filter(role='responsable_rh').count(),
                'technicien': roles.filter(role='technicien').count(),
                'securite': roles.filter(role='securite').count(),
                'acheteur': roles.filter(role='acheteur').count(),
                'responsable_qualite': roles.filter(role='responsable_qualite').count(),
                'assistant_rh': roles.filter(role='assistant_rh').count(),
                'formateur': roles.filter(role='formateur').count(),
                'assistant_chantier': roles.filter(role='assistant_chantier').count(),
                'assistant_admin': roles.filter(role='assistant_admin').count(),
            },
            'roles_disponibles': [{'value': r[0], 'label': r[1]} for r in agence.get_roles_disponibles()]
        }
        return Response(stats)


class RoleAgenceViewset(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleAgenceSerializer
    queryset = RoleAgence.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.est_pdg():
            return RoleAgence.objects.filter(est_actif=True)
        agences_ids = user.roles_agence.filter(
            est_actif=True).values_list('agence_id', flat=True)
        return RoleAgence.objects.filter(agence_id__in=agences_ids, est_actif=True)

    def create(self, request, *args, **kwargs):
        if not request.user.est_pdg():
            return Response({"error": "Seul le PDG peut assigner des rôles"}, status=403)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "Paramètre 'user_id' requis"}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)
        if not (request.user.est_pdg()):
            if request.user.id != int(user_id):
                return Response({"error": "Permission denied"}, status=403)
        roles = user.roles_agence.filter(est_actif=True).select_related('agence')
        serializer = RoleAgenceSerializer(roles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_agence(self, request):
        agence_id = request.query_params.get('agence_id')
        if not agence_id:
            return Response({"error": "Paramètre 'agence_id' requis"}, status=400)
        try:
            agence = Agence.objects.get(id=agence_id)
        except Agence.DoesNotExist:
            return Response({"error": "Agence non trouvée"}, status=404)
        if not (request.user.est_pdg() or request.user.peut_acceder_agence(agence_id)):
            return Response({"error": "Permission denied"}, status=403)
        roles = agence.roles.filter(est_actif=True).select_related('user')
        serializer = RoleAgenceSerializer(roles, many=True)
        return Response(serializer.data)


class AgencesPubliquesViewset(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        agences = Agence.objects.filter(est_active=True)
        serializer = AgenceSerializer(agences, many=True)
        return Response(serializer.data)