from rest_framework.exceptions import APIException

class InsufficientStockException(APIException):
    """Когда есть остаток, но его недостаточно для запроса"""
    status_code = 409
    default_code = 'INSUFFICIENT_STOCK'
    default_detail = 'Недостаточно остатка на складе'
    
    def __init__(self, sku_id=None, sku_name=None, available=None, requested=None):
        self.sku_id = sku_id
        self.sku_name = sku_name
        self.available = available
        self.requested = requested
        self.detail = {
            'sku_id': sku_id,
            'sku_name': sku_name,
            'available': available,
            'requested': requested
        }


class OutOfStockException(APIException):
    """Когда остаток равен 0"""
    status_code = 409
    default_code = 'OUT_OF_STOCK'
    default_detail = 'Товар отсутствует на складе'
    
    def __init__(self, sku_id=None, sku_name=None):
        self.sku_id = sku_id
        self.sku_name = sku_name
        self.detail = {
            'sku_id': sku_id,
            'sku_name': sku_name
        }
