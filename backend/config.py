"""
Configuration module for QualGent Job Orchestrator

This module handles configuration for Redis, storage options, and other settings.
"""

import os
from typing import Optional


class Config:
    """Configuration class for application settings"""
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    USE_REDIS = os.environ.get('USE_REDIS', 'true').lower() == 'true'
    
    # Server Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # Job Configuration
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
    WORKER_TIMEOUT = int(os.environ.get('WORKER_TIMEOUT', 300))  # seconds
    SCHEDULE_INTERVAL = int(os.environ.get('SCHEDULE_INTERVAL', 5))  # seconds
    
    # Security (for production)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @classmethod
    def get_redis_config(cls) -> dict:
        """Get Redis configuration"""
        return {
            'url': cls.REDIS_URL,
            'enabled': cls.USE_REDIS
        }
    
    @classmethod
    def get_server_config(cls) -> dict:
        """Get server configuration"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'debug': cls.DEBUG
        }
    
    @classmethod
    def get_job_config(cls) -> dict:
        """Get job processing configuration"""
        return {
            'max_retries': cls.MAX_RETRIES,
            'worker_timeout': cls.WORKER_TIMEOUT,
            'schedule_interval': cls.SCHEDULE_INTERVAL
        }


# Development configuration
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_REDIS = False  # Use in-memory for easier development


# Production configuration
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_REDIS = True
    HOST = '0.0.0.0'
    PORT = 5000


# Configuration factory
def get_config(environment: Optional[str] = None) -> Config:
    """Get configuration based on environment"""
    env = environment or os.environ.get('ENVIRONMENT', 'development')
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'development':
        return DevelopmentConfig()
    else:
        return Config() 