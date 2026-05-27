from rest_framework.pagination import LimitOffsetPagination


class B2CProductPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100
