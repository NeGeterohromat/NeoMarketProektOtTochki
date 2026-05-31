from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class B2CProductPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response({
            'items': data,
            'total_count': self.count,
            'limit': self.limit,
            'offset': self.offset,
        })
