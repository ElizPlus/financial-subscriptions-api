from app import db
from datetime import datetime, timedelta
from enum import Enum
import json

class Periodicity(Enum):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    periodicity = db.Column(db.Enum(Periodicity), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    next_payment_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_next_payment(self):
        if self.periodicity == Periodicity.DAILY:
            return self.next_payment_date + timedelta(days=1)
        elif self.periodicity == Periodicity.WEEKLY:
            return self.next_payment_date + timedelta(weeks=1)
        elif self.periodicity == Periodicity.MONTHLY:
            return self.next_payment_date + timedelta(days=30)
        elif self.periodicity == Periodicity.QUARTERLY:
            return self.next_payment_date + timedelta(days=90)
        elif self.periodicity == Periodicity.YEARLY:
            return self.next_payment_date + timedelta(days=365)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)