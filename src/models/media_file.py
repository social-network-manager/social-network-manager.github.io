from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import hashlib
import os

db = SQLAlchemy()

class MediaFile(db.Model):
    __tablename__ = 'media_files'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_hash = db.Column(db.String(64), unique=True)
    alt_text = db.Column(db.Text)
    file_metadata = db.Column(db.Text, default='{}')  # JSON metadata
    processing_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('media_files', lazy=True))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.file_path and not self.file_hash:
            self.file_hash = self.calculate_file_hash()
    
    def calculate_file_hash(self):
        """Calculate SHA-256 hash of the file"""
        if not os.path.exists(self.file_path):
            return None
        
        hash_sha256 = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def set_metadata(self, metadata_dict):
        """Store metadata as JSON"""
        self.file_metadata = json.dumps(metadata_dict)
    
    def get_metadata(self):
        """Get metadata as dict"""
        if not self.file_metadata:
            return {}
        return json.loads(self.file_metadata)
    
    def get_file_extension(self):
        """Get file extension from original filename"""
        return os.path.splitext(self.original_filename)[1].lower()
    
    def is_image(self):
        """Check if file is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        return self.mime_type in image_types
    
    def is_video(self):
        """Check if file is a video"""
        video_types = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/webm']
        return self.mime_type in video_types
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_mb': self.get_file_size_mb(),
            'mime_type': self.mime_type,
            'file_hash': self.file_hash,
            'alt_text': self.alt_text,
            'metadata': self.get_metadata(),
            'processing_status': self.processing_status,
            'is_image': self.is_image(),
            'is_video': self.is_video(),
            'file_extension': self.get_file_extension(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<MediaFile {self.id}:{self.original_filename}>'

