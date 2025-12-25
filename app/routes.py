from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Subscription, User, AuditLog, Periodicity
from app.auth import token_required, login_user, register_user, create_token
from app.validators import validate_subscription_data, sanitize_input
from app.database import create_audit_log, get_upcoming_payments
from datetime import datetime
import json

api_bp = Blueprint('api', __name__)

# Новый endpoint для аутентификации
@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.get_json()
    
    if not data or 'email' not in data or 'username' not in data:
        return jsonify({'error': 'Email and username are required'}), 400
    
    user, error = register_user(data['username'], data['email'], data.get('password'))
    
    if error:
        return jsonify({'error': error}), 400
    
    token = create_token(user.id)
    
    return jsonify({
        'message': 'User registered successfully',
        'token': token,
        'user_id': user.id
    }), 201

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Аутентификация пользователя"""
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    token, error = login_user(data['email'], data.get('password'))
    
    if error:
        return jsonify({'error': error}), 401
    
    return jsonify({
        'message': 'Login successful',
        'token': token
    }), 200

# Обновите другие endpoints с использованием валидации
@api_bp.route('/subscriptions', methods=['POST'])
@token_required  # Теперь требуется аутентификация
def create_subscription():
    """Создание новой подписки"""
    try:
        data = request.get_json()
        
        # Санитизация входных данных
        data = sanitize_input(data)
        
        # Валидация
        validation_errors = validate_subscription_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Проверка периодичности
        try:
            periodicity = Periodicity(data['periodicity'])
        except ValueError:
            return jsonify({'error': 'Invalid periodicity'}), 400
        
        # Преобразование даты
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        # Создание подписки (теперь используем g.current_user из декоратора)
        subscription = Subscription(
            user_id=g.current_user.id,  # Берем ID из токена
            name=data['name'],
            amount=float(data['amount']),
            periodicity=periodicity,
            start_date=start_date,
            next_payment_date=start_date,
            is_active=True
        )
        
        db.session.add(subscription)
        db.session.flush()  # Получаем ID до коммита
        
        # Логирование в аудит
        create_audit_log(
            user_id=g.current_user.id,
            action='CREATE',
            table_name='subscriptions',
            record_id=subscription.id,
            new_values=data
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription created successfully',
            'subscription': {
                'id': subscription.id,
                'name': subscription.name,
                'amount': subscription.amount,
                'periodicity': subscription.periodicity.value,
                'start_date': subscription.start_date.isoformat(),
                'next_payment_date': subscription.next_payment_date.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/subscriptions', methods=['GET'])
@token_required
def get_subscriptions():
    """Получение всех активных подписок пользователя"""
    try:
        subscriptions = Subscription.query.filter_by(
            user_id=g.current_user.id, 
            is_active=True
        ).all()
        
        result = []
        for sub in subscriptions:
            result.append({
                'id': sub.id,
                'name': sub.name,
                'amount': sub.amount,
                'periodicity': sub.periodicity.value,
                'start_date': sub.start_date.isoformat(),
                'next_payment_date': sub.next_payment_date.isoformat(),
                'is_active': sub.is_active,
                'created_at': sub.created_at.isoformat()
            })
        
        return jsonify({'subscriptions': result}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/subscriptions/<int:subscription_id>', methods=['PUT'])
@token_required
def update_subscription(subscription_id):
    """Обновление информации о подписке"""
    try:
        data = request.get_json()
        subscription = Subscription.query.filter_by(
            id=subscription_id, 
            user_id=g.current_user.id
        ).first()
        
        if not subscription:
            return jsonify({'error': 'Subscription not found'}), 404
        
        # Санитизация данных
        data = sanitize_input(data)
        
        # Валидация
        validation_errors = validate_subscription_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Сохраняем старые значения для аудита
        old_values = {
            'name': subscription.name,
            'amount': subscription.amount,
            'periodicity': subscription.periodicity.value,
            'next_payment_date': subscription.next_payment_date.isoformat()
        }
        
        # Обновляем поля
        if 'name' in data:
            subscription.name = data['name']
        if 'amount' in data:
            subscription.amount = float(data['amount'])
        if 'periodicity' in data:
            subscription.periodicity = Periodicity(data['periodicity'])
        if 'next_payment_date' in data:
            subscription.next_payment_date = datetime.strptime(
                data['next_payment_date'], '%Y-%m-%d'
            ).date()
        
        # Логирование в аудит
        new_values = {
            'name': subscription.name,
            'amount': subscription.amount,
            'periodicity': subscription.periodicity.value,
            'next_payment_date': subscription.next_payment_date.isoformat()
        }
        
        create_audit_log(
            user_id=g.current_user.id,
            action='UPDATE',
            table_name='subscriptions',
            record_id=subscription.id,
            old_values=old_values,
            new_values=new_values
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription updated successfully',
            'subscription': {
                'id': subscription.id,
                'name': subscription.name,
                'amount': subscription.amount,
                'periodicity': subscription.periodicity.value,
                'next_payment_date': subscription.next_payment_date.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/subscriptions/<int:subscription_id>', methods=['DELETE'])
@token_required
def delete_subscription(subscription_id):
    """Удаление подписки (мягкое удаление)"""
    try:
        subscription = Subscription.query.filter_by(
            id=subscription_id, 
            user_id=g.current_user.id
        ).first()
        
        if not subscription:
            return jsonify({'error': 'Subscription not found'}), 404
        
        # Мягкое удаление
        subscription.is_active = False
        
        # Логирование в аудит
        create_audit_log(
            user_id=g.current_user.id,
            action='DELETE',
            table_name='subscriptions',
            record_id=subscription.id,
            old_values={
                'name': subscription.name,
                'amount': subscription.amount,
                'periodicity': subscription.periodicity.value
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Новый endpoint для предстоящих платежей
@api_bp.route('/subscriptions/upcoming', methods=['GET'])
@token_required
def get_upcoming():
    """Получение предстоящих платежей"""
    days_ahead = request.args.get('days', default=30, type=int)
    
    upcoming = get_upcoming_payments(g.current_user.id, days_ahead)
    
    result = []
    for sub in upcoming:
        result.append({
            'id': sub.id,
            'name': sub.name,
            'amount': sub.amount,
            'next_payment_date': sub.next_payment_date.isoformat(),
            'days_until': (sub.next_payment_date - datetime.now().date()).days
        })
    
    return jsonify({
        'upcoming_payments': result,
        'total_amount': sum(sub.amount for sub in upcoming)
    }), 200

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья приложения"""
    return jsonify({'status': 'healthy'}), 200