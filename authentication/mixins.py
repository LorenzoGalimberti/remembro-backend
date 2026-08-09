class UserFilteredQuerysetMixin:
    """
    Mixin per ViewSet/generics DRF: filtra automaticamente il queryset
    in base all'utente autenticato.

    Imposta `owner_lookup` sulla view con la sintassi ORM per raggiungere
    lo user (es. 'user' per Category/Notion, 'notion__user' per Card).
    """
    owner_lookup = 'user'

    def get_queryset(self):
        return super().get_queryset().filter(**{self.owner_lookup: self.request.user})
