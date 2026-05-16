import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bar-management-secret-key-2026'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///bar_management.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SBIS API - DeepSeek OAuth format
    SBIS_CLIENT_ID = os.environ.get('SBIS_CLIENT_ID', '')
    SBIS_APP_SECRET = os.environ.get('SBIS_APP_SECRET', '')
    SBIS_SECRET_KEY = os.environ.get('SBIS_SECRET_KEY', '')
    SBIS_TOKEN = os.environ.get('SBIS_TOKEN', '')
    SBIS_HOST = os.environ.get('SBIS_HOST', 'api.sbis.ru')
    
    # App settings
    PROMO_DISCOUNT_THRESHOLD = 15  # % — минимальная скидка для определения акции
    KEG_LOW_THRESHOLD = 5  # liters
    KEG_WARNING_THRESHOLD = 10  # liters
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
