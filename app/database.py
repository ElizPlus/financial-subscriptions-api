from app import db
from app.models import AuditLog, Subscription
from datetime import datetime
import json

def create_audit_log(user_id, action, table_name, record_id, old_values=None, new_values=None):
    """Создание записи в логе аудита"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None
    )
    
    try:
        db.session.add(audit_log)
        db.session.commit()
        return audit_log
    except Exception as e:
        db.session.rollback()
        print(f"Error creating audit log: {e}")
        return None

def get_user_subscriptions(user_id, active_only=True):
    """Получение подписок пользователя"""
    query = Subscription.query.filter_by(user_id=user_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    return query.order_by(Subscription.next_payment_date).all()

def update_subscription_next_payment(subscription_id):
    """Обновление даты следующего платежа"""
    subscription = Subscription.query.get(subscription_id)
    
    if not subscription:
        return None, "Subscription not found"
    
    try:
        old_date = subscription.next_payment_date
        subscription.next_payment_date = subscription.calculate_next_payment()
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Логируем изменение
        create_audit_log(
            user_id=subscription.user_id,
            action='UPDATE_NEXT_PAYMENT',
            table_name='subscriptions',
            record_id=subscription.id,
            old_values={'next_payment_date': old_date.isoformat()},
            new_values={'next_payment_date': subscription.next_payment_date.isoformat()}
        )
        
        return subscription, None
    except Exception as e:
        db.session.rollback()
        return None, str(e)

def get_upcoming_payments(user_id, days_ahead=30):
    """Получение предстоящих платежей"""
    from datetime import date, timedelta
    
    end_date = date.today() + timedelta(days=days_ahead)
    
    subscriptions = Subscription.query.filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True,
        Subscription.next_payment_date <= end_date,
        Subscription.next_payment_date >= date.today()
    ).order_by(Subscription.next_payment_date).all()
    
    return subscriptions

def get_monthly_summary(user_id, year, month):
    """Получение месячной статистики по подпискам"""
    from datetime import date
    from sqlalchemy import extract
    
    # Подписки, активные в указанном месяце
    subscriptions = Subscription.query.filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True,
        extract('year', Subscription.start_date) <= year,
        extract('month', Subscription.start_date) <= month
    ).all()
    
    total_amount = sum(sub.amount for sub in subscriptions)
    
    # Платежи в указанном месяце
    payments = []
    for sub in subscriptions:
        # Здесь должна быть логика расчета всех платежей в месяце
        # Для простоты считаем только если next_payment_date в этом месяце
        if (sub.next_payment_date.year == year and 
            sub.next_payment_date.month == month):
            payments.append({
                'subscription': sub.name,
                'amount': sub.amount,
                'date': sub.next_payment_date
            })
    
    return {
        'total_subscriptions': len(subscriptions),
        'total_monthly_amount': total_amount,
        'upcoming_payments': payments
    }