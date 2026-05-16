from rest_framework.views import exception_handler

def get_first_error(data):
    """Рекурсивно извлекает первую ошибку (код или текст) из структуры DRF"""
    if isinstance(data, dict):
        if not data:
            return None
        first_key = next(iter(data))
        # Сохраняем имя поля для контекста сообщения, если это не служебный ключ
        field_prefix = f"{first_key}: " if first_key not in ('non_field_errors', 0) else ""
        res = get_first_error(data[first_key])
        if isinstance(res, tuple):
            return field_prefix + res[0], res[1]
        return field_prefix + str(res) if res else None
        
    elif isinstance(data, list):
        if not data:
            return None
        return get_first_error(data[0])
        
    return str(data)

def custom_exception_handler(exc, context):
    """
    Меняет стандартный ответ при исключении на формат {"code": "...", "message": "..."}
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Получаем чистый строковый код ошибки
        error_code = 'error'
        if hasattr(exc, 'get_codes'):
            raw_codes = exc.get_codes()
            extracted_code = get_first_error(raw_codes)
            if extracted_code:
                # Если вернулся префикс поля (например, "images: min_length"), берем только сам код
                error_code = extracted_code.split(': ')[-1]
        else:
            error_code = getattr(exc, 'default_code', 'error')

        # Получаем чистое текстовое сообщение
        raw_data = response.data
        extracted_msg = get_first_error(raw_data)
        
        message = extracted_msg if extracted_msg else "Unknown error"

        response.data = {
            "code": str(error_code),
            "message": str(message)
        }

    return response
