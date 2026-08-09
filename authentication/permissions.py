from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission a livello di oggetto: verifica che l'utente autenticato
    sia il proprietario dell'oggetto.

    Supporta sia un campo diretto ('user') sia un percorso annidato
    (es. 'notion.user' per Card, che non ha un campo user proprio).
    Il percorso si imposta sulla view con l'attributo `owner_path`.
    """
    default_owner_path = 'user'

    def has_object_permission(self, request, view, obj):
        owner_path = getattr(view, 'owner_path', self.default_owner_path)
        owner = obj
        for attr in owner_path.split('.'):
            owner = getattr(owner, attr)
        return owner == request.user
