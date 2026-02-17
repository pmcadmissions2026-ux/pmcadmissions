import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', False)
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', 3600))
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', False)
    
    # Supabase Configuration
    _supabase_url = os.getenv('SUPABASE_URL')
    _supabase_key = os.getenv('SUPABASE_KEY')
    _supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

    SUPABASE_URL = _supabase_url.strip() if _supabase_url else None
    SUPABASE_KEY = _supabase_key.strip() if _supabase_key else None
    SUPABASE_SERVICE_KEY = _supabase_service_key.strip() if _supabase_service_key else None
    
    # College Configuration
    COLLEGE_NAME = os.getenv('COLLEGE_NAME', 'Er. Perumal Manimekalai College of Engineering')
    COLLEGE_ACRONYM = os.getenv('COLLEGE_ACRONYM', 'PMC')
    ACADEMIC_YEAR = os.getenv('ACADEMIC_YEAR', '2025-2026')

    # EmailJS Configuration (set these in your .env)
    EMAILJS_SERVICE_ID = os.getenv('EMAILJS_SERVICE_ID', 'service_j9uyccf')
    EMAILJS_TEMPLATE_ID = os.getenv('EMAILJS_TEMPLATE_ID', 'template_2yyrt7d')
    # Updated API / public key provided by user
    EMAILJS_PUBLIC_KEY = os.getenv('EMAILJS_PUBLIC_KEY', '7cI3UOLBouyhfc_C3')
    # SMTP fallback configuration
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True')
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
