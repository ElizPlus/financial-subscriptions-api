from functools import wraps
from flask import request, jsonify, g
import jwt
import datetime
from app import db
from app.models import User

def create_token(user_id):
    """Создание JWT токена"""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    token = jwt.encode(payload, 'your-secret-key', algorithm='HS256')
    return token

def token_required(f):
    """Декоратор для проверки JWT токена"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Проверяем заголовок Authorization
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Декодируем токен
            data = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
                
            # Сохраняем пользователя в g контексте
            g.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def register_user(username, email, password):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return None, 'User already exists'
    
    # Создаем нового пользователя
    user = User(
        username=username,
        email=email
        # В реальном приложении здесь должно быть хеширование пароля
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as e:
        db.session.rollback()
        return None, str(e)

def login_user(email, password):
    """Аутентификация пользователя"""
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return None, 'User not found'
    
    # В реальном приложении здесь должно быть проверка пароля
    # if not check_password_hash(user.password, password):
    #     return None, 'Invalid password'
    
    # Создаем токен
    token = create_token(user.id)
    return token, None