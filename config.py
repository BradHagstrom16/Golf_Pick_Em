"""
Golf Pick 'Em League - Configuration
=====================================
Configuration settings for different environments.
"""

import os
from datetime import timedelta

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'golf_pickem.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # League Settings
    LEAGUE_TIMEZONE = 'America/Chicago'
    SEASON_YEAR = 2026
    ENTRY_FEE = 25  # dollars
    
    # SlashGolf API (via RapidAPI)
    SLASHGOLF_API_KEY = os.environ.get('SLASHGOLF_API_KEY')
    SLASHGOLF_API_HOST = 'live-golf-data.p.rapidapi.com'
    SLASHGOLF_ORG_ID = '1'  # PGA Tour
    
    # Feature flags
    PICKS_VISIBLE_AFTER_DEADLINE = True  # Show everyone's picks after deadline


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Override these in production environment
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
