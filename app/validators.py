from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.models import Periodicity

class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)

def validate_subscription_data(data):
    """Валидация данных для создания/обновления подписки"""
    errors = {}
    
    # Проверка названия
    if 'name' in data:
        if not data['name'] or len(data['name'].strip()) == 0:
            errors['name'] = 'Name is required'
        elif len(data['name']) > 100:
            errors['name'] = 'Name must be less than 100 characters'
    
    # Проверка суммы
    if 'amount' in data:
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                errors['amount'] = 'Amount must be greater than 0'
            elif amount > 1000000:  # Максимальная сумма
                errors['amount'] = 'Amount is too large'
        except (ValueError, InvalidOperation):
            errors['amount'] = 'Invalid amount format'
    
    # Проверка периодичности
    if 'periodicity' in data:
        try:
            periodicity = Periodicity(data['periodicity'])
        except ValueError:
            errors['periodicity'] = f'Invalid periodicity. Must be one of: {[p.value for p in Periodicity]}'
    
    # Проверка даты начала
    if 'start_date' in data:
        try:
            date_obj = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            #if date_obj < datetime.now().date():
             #   errors['start_date'] = 'Start date cannot be in the past'
        except ValueError:
            errors['start_date'] = 'Invalid date format. Use YYYY-MM-DD'
    
    # Проверка даты следующего платежа (при обновлении)
    if 'next_payment_date' in data:
        try:
            date_obj = datetime.strptime(data['next_payment_date'], '%Y-%m-%d').date()
            if date_obj < datetime.now().date():
                errors['next_payment_date'] = 'Next payment date cannot be in the past'
        except ValueError:
            errors['next_payment_date'] = 'Invalid date format. Use YYYY-MM-DD'
    
    return errors

def validate_user_data(data):
    """Валидация данных пользователя"""
    errors = {}
    
    # Проверка email
    if 'email' in data:
        email = data['email'].strip()
        if not email:
            errors['email'] = 'Email is required'
        elif '@' not in email or '.' not in email:
            errors['email'] = 'Invalid email format'
        elif len(email) > 120:
            errors['email'] = 'Email must be less than 120 characters'
    
    # Проверка имени пользователя
    if 'username' in data:
        username = data['username'].strip()
        if not username:
            errors['username'] = 'Username is required'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters'
        elif len(username) > 80:
            errors['username'] = 'Username must be less than 80 characters'
    
    return errors

def sanitize_input(data):
    """Санитизация входных данных"""
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Удаляем лишние пробелы
            sanitized[key] = value.strip()
            # Заменяем опасные символы (базовая защита от XSS)
            sanitized[key] = sanitized[key].replace('<', '&lt;').replace('>', '&gt;')
        else:
            sanitized[key] = value
    
    return sanitized

def validate_date_range(start_date_str, end_date_str):
    """Валидация диапазона дат"""
    errors = {}
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        errors['start_date'] = 'Invalid start date format'
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        errors['end_date'] = 'Invalid end date format'
    
    if not errors:
        if start_date > end_date:
            errors['date_range'] = 'Start date must be before end date'
    
    return errors

# Валидаторы для конкретных типов данных
def validate_periodicity(value):
    """Валидация значения периодичности"""
    try:
        return Periodicity(value), None
    except ValueError:
        valid_values = [p.value for p in Periodicity]
        return None, f"Invalid periodicity. Must be one of: {valid_values}"

def validate_amount(value):
    """Валидация денежной суммы"""
    try:
        amount = Decimal(str(value))
        if amount <= 0:
            return None, "Amount must be greater than 0"
        return amount, None
    except (ValueError, InvalidOperation):
        return None, "Invalid amount format"

def validate_date(value, field_name="date"):
    """Валидация даты"""
    try:
        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
        return date_obj, None
    except ValueError:
        return None, f"Invalid {field_name} format. Use YYYY-MM-DD"