from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class ContentPost(db.Model):
    __tablename__ = 'content_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), default='text')
    media_attachments = db.Column(db.Text, default='[]')  # JSON array of media files
    hashtags = db.Column(db.Text)  # JSON array of hashtags
    mentions = db.Column(db.Text)  # JSON array of mentions
    platform_specific_content = db.Column(db.Text, default='{}')  # JSON object
    status = db.Column(db.String(20), default='draft')
    scheduled_for = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('content_posts', lazy=True))
    
    def set_media_attachments(self, media_list):
        """Store media attachments as JSON"""
        self.media_attachments = json.dumps(media_list)
    
    def get_media_attachments(self):
        """Get media attachments as list"""
        if not self.media_attachments:
            return []
        return json.loads(self.media_attachments)
    
    def set_hashtags(self, hashtag_list):
        """Store hashtags as JSON"""
        self.hashtags = json.dumps(hashtag_list)
    
    def get_hashtags(self):
        """Get hashtags as list"""
        if not self.hashtags:
            return []
        return json.loads(self.hashtags)
    
    def set_mentions(self, mention_list):
        """Store mentions as JSON"""
        self.mentions = json.dumps(mention_list)
    
    def get_mentions(self):
        """Get mentions as list"""
        if not self.mentions:
            return []
        return json.loads(self.mentions)
    
    def set_platform_content(self, platform_content_dict):
        """Store platform-specific content as JSON"""
        self.platform_specific_content = json.dumps(platform_content_dict)
    
    def get_platform_content(self):
        """Get platform-specific content"""
        if not self.platform_specific_content:
            return {}
        return json.loads(self.platform_specific_content)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'content_type': self.content_type,
            'media_attachments': self.get_media_attachments(),
            'hashtags': self.get_hashtags(),
            'mentions': self.get_mentions(),
            'platform_content': self.get_platform_content(),
            'status': self.status,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'published_at': self.published_at.isoformat() if self.published_at else None
        }
    
    def __repr__(self):
        return f'<ContentPost {self.id}:{self.title}>'


class PostDistribution(db.Model):
    __tablename__ = 'post_distributions'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('content_posts.id'), nullable=False)
    social_media_account_id = db.Column(db.Integer, db.ForeignKey('social_media_accounts.id'), nullable=False)
    platform_post_id = db.Column(db.String(255))
    distribution_status = db.Column(db.String(20), default='pending')
    scheduled_for = db.Column(db.DateTime)
    attempted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    platform_response = db.Column(db.Text)  # JSON response from platform
    engagement_metrics = db.Column(db.Text, default='{}')  # JSON metrics
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    post = db.relationship('ContentPost', backref=db.backref('distributions', lazy=True))
    social_account = db.relationship('SocialMediaAccount', backref=db.backref('distributions', lazy=True))
    
    def set_platform_response(self, response_dict):
        """Store platform response as JSON"""
        self.platform_response = json.dumps(response_dict)
    
    def get_platform_response(self):
        """Get platform response"""
        if not self.platform_response:
            return {}
        return json.loads(self.platform_response)
    
    def set_engagement_metrics(self, metrics_dict):
        """Store engagement metrics as JSON"""
        self.engagement_metrics = json.dumps(metrics_dict)
    
    def get_engagement_metrics(self):
        """Get engagement metrics"""
        if not self.engagement_metrics:
            return {}
        return json.loads(self.engagement_metrics)
    
    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'social_media_account_id': self.social_media_account_id,
            'platform_post_id': self.platform_post_id,
            'distribution_status': self.distribution_status,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'attempted_at': self.attempted_at.isoformat() if self.attempted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'platform_response': self.get_platform_response(),
            'engagement_metrics': self.get_engagement_metrics(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<PostDistribution {self.id}:{self.distribution_status}>'

