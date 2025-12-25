# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Если передан тестовый конфиг, используем его
    if test_config is None:
        # Конфигурация для разработки/продакшена
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = False
    else:
        # Конфигурация для тестов
        app.config.update(test_config)
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Регистрация маршрутов
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Создание таблиц при запуске (только если не в тестовом режиме)
    if not app.config.get('TESTING'):
        with app.app_context():
            db.create_all()
    
    return app