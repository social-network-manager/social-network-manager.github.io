from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from cryptography.fernet import Fernet
import os

db = SQLAlchemy()

class SocialMediaAccount(db.Model):
    __tablename__ = 'social_media_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    platform_user_id = db.Column(db.String(255))
    username = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    profile_image_url = db.Column(db.Text)
    encrypted_credentials = db.Column(db.Text, nullable=False)
    connection_status = db.Column(db.String(20), default='active')
    last_successful_post = db.Column(db.DateTime)
    last_authentication = db.Column(db.DateTime, default=datetime.utcnow)
    authentication_expires_at = db.Column(db.DateTime)
    platform_specific_settings = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('social_accounts', lazy=True))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, '_encryption_key'):
            self._encryption_key = self._get_encryption_key()
    
    def _get_encryption_key(self):
        """Get or create encryption key for this account"""
        key_file = f'/tmp/social_account_{self.user_id}_{self.platform}.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def set_credentials(self, credentials_dict):
        """Encrypt and store credentials"""
        credentials_json = json.dumps(credentials_dict)
        fernet = Fernet(self._encryption_key)
        self.encrypted_credentials = fernet.encrypt(credentials_json.encode()).decode()
    
    def get_credentials(self):
        """Decrypt and return credentials"""
        if not self.encrypted_credentials:
            return {}
        fernet = Fernet(self._encryption_key)
        decrypted_data = fernet.decrypt(self.encrypted_credentials.encode())
        return json.loads(decrypted_data.decode())
    
    def set_platform_settings(self, settings_dict):
        """Store platform-specific settings as JSON"""
        self.platform_specific_settings = json.dumps(settings_dict)
    
    def get_platform_settings(self):
        """Get platform-specific settings"""
        if not self.platform_specific_settings:
            return {}
        return json.loads(self.platform_specific_settings)
    
    def is_authenticated(self):
        """Check if account is currently authenticated"""
        if self.connection_status != 'active':
            return False
        if self.authentication_expires_at and self.authentication_expires_at < datetime.utcnow():
            return False
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'platform_user_id': self.platform_user_id,
            'username': self.username,
            'display_name': self.display_name,
            'profile_image_url': self.profile_image_url,
            'connection_status': self.connection_status,
            'last_successful_post': self.last_successful_post.isoformat() if self.last_successful_post else None,
            'last_authentication': self.last_authentication.isoformat() if self.last_authentication else None,
            'authentication_expires_at': self.authentication_expires_at.isoformat() if self.authentication_expires_at else None,
            'platform_settings': self.get_platform_settings(),
            'is_authenticated': self.is_authenticated(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<SocialMediaAccount {self.platform}:{self.username}>'

