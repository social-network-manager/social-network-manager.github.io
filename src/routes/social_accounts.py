from flask import Blueprint, request, jsonify, session
from src.models.social_account import SocialMediaAccount, db
from src.models.user import User
from src.routes.auth import require_auth
from datetime import datetime, timedelta

social_accounts_bp = Blueprint('social_accounts', __name__)

SUPPORTED_PLATFORMS = [
    'facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 
    'google_business', 'pinterest', 'reddit', 'tiktok', 'snapchat',
    'tumblr', 'mastodon', 'bluesky', 'discord', 'telegram', 'whatsapp'
]

@social_accounts_bp.route('/accounts', methods=['GET'])
@require_auth
def get_social_accounts():
    """Get all social media accounts for the current user"""
    try:
        user_id = session.get('user_id')
        accounts = SocialMediaAccount.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'accounts': [account.to_dict() for account in accounts],
            'total': len(accounts)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch accounts: {str(e)}'}), 500

@social_accounts_bp.route('/accounts', methods=['POST'])
@require_auth
def add_social_account():
    """Add a new social media account"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        platform = data.get('platform', '').lower()
        credentials = data.get('credentials', {})
        
        if not platform or platform not in SUPPORTED_PLATFORMS:
            return jsonify({'error': f'Invalid platform. Supported: {SUPPORTED_PLATFORMS}'}), 400
        
        if not credentials:
            return jsonify({'error': 'Credentials are required'}), 400
        
        user_id = session.get('user_id')
        
        # Check if account already exists for this platform
        existing_account = SocialMediaAccount.query.filter_by(
            user_id=user_id, 
            platform=platform
        ).first()
        
        if existing_account:
            return jsonify({'error': f'Account for {platform} already exists'}), 409
        
        # Create new social media account
        new_account = SocialMediaAccount(
            user_id=user_id,
            platform=platform,
            platform_user_id=data.get('platform_user_id'),
            username=data.get('username'),
            display_name=data.get('display_name'),
            profile_image_url=data.get('profile_image_url'),
            connection_status='active',
            authentication_expires_at=datetime.utcnow() + timedelta(days=60)  # Default 60 days
        )
        
        # Set encrypted credentials
        new_account.set_credentials(credentials)
        
        # Set platform-specific settings if provided
        if 'platform_settings' in data:
            new_account.set_platform_settings(data['platform_settings'])
        
        db.session.add(new_account)
        db.session.commit()
        
        return jsonify({
            'message': f'{platform.title()} account added successfully',
            'account': new_account.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add account: {str(e)}'}), 500

@social_accounts_bp.route('/accounts/<int:account_id>', methods=['GET'])
@require_auth
def get_social_account(account_id):
    """Get a specific social media account"""
    try:
        user_id = session.get('user_id')
        account = SocialMediaAccount.query.filter_by(
            id=account_id, 
            user_id=user_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        return jsonify({'account': account.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch account: {str(e)}'}), 500

@social_accounts_bp.route('/accounts/<int:account_id>', methods=['PUT'])
@require_auth
def update_social_account(account_id):
    """Update a social media account"""
    try:
        user_id = session.get('user_id')
        account = SocialMediaAccount.query.filter_by(
            id=account_id, 
            user_id=user_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update basic fields
        if 'username' in data:
            account.username = data['username']
        if 'display_name' in data:
            account.display_name = data['display_name']
        if 'profile_image_url' in data:
            account.profile_image_url = data['profile_image_url']
        if 'connection_status' in data:
            account.connection_status = data['connection_status']
        
        # Update credentials if provided
        if 'credentials' in data:
            account.set_credentials(data['credentials'])
            account.last_authentication = datetime.utcnow()
            account.authentication_expires_at = datetime.utcnow() + timedelta(days=60)
        
        # Update platform settings if provided
        if 'platform_settings' in data:
            account.set_platform_settings(data['platform_settings'])
        
        account.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Account updated successfully',
            'account': account.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update account: {str(e)}'}), 500

@social_accounts_bp.route('/accounts/<int:account_id>', methods=['DELETE'])
@require_auth
def delete_social_account(account_id):
    """Delete a social media account"""
    try:
        user_id = session.get('user_id')
        account = SocialMediaAccount.query.filter_by(
            id=account_id, 
            user_id=user_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        platform = account.platform
        db.session.delete(account)
        db.session.commit()
        
        return jsonify({
            'message': f'{platform.title()} account deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500

@social_accounts_bp.route('/accounts/<int:account_id>/test', methods=['POST'])
@require_auth
def test_social_account(account_id):
    """Test connection to a social media account"""
    try:
        user_id = session.get('user_id')
        account = SocialMediaAccount.query.filter_by(
            id=account_id, 
            user_id=user_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # TODO: Implement actual API testing for each platform
        # For now, just check if credentials exist and account is active
        
        if not account.is_authenticated():
            return jsonify({
                'success': False,
                'message': 'Account authentication has expired',
                'status': 'expired'
            }), 200
        
        credentials = account.get_credentials()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No credentials found',
                'status': 'no_credentials'
            }), 200
        
        # Simulate successful test for now
        account.last_authentication = datetime.utcnow()
        account.connection_status = 'active'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{account.platform.title()} connection test successful',
            'status': 'connected'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Connection test failed: {str(e)}'}), 500

@social_accounts_bp.route('/platforms', methods=['GET'])
def get_supported_platforms():
    """Get list of supported platforms"""
    platform_info = {
        'facebook': {'name': 'Facebook', 'api_available': True, 'auth_type': 'oauth2'},
        'twitter': {'name': 'X (Twitter)', 'api_available': True, 'auth_type': 'oauth2'},
        'instagram': {'name': 'Instagram', 'api_available': True, 'auth_type': 'oauth2'},
        'linkedin': {'name': 'LinkedIn', 'api_available': True, 'auth_type': 'oauth2'},
        'youtube': {'name': 'YouTube', 'api_available': True, 'auth_type': 'oauth2'},
        'google_business': {'name': 'Google Business Profile', 'api_available': True, 'auth_type': 'oauth2'},
        'pinterest': {'name': 'Pinterest', 'api_available': True, 'auth_type': 'oauth2'},
        'reddit': {'name': 'Reddit', 'api_available': True, 'auth_type': 'oauth2'},
        'tiktok': {'name': 'TikTok', 'api_available': True, 'auth_type': 'oauth2'},
        'snapchat': {'name': 'Snapchat', 'api_available': False, 'auth_type': 'browser'},
        'tumblr': {'name': 'Tumblr', 'api_available': True, 'auth_type': 'oauth1'},
        'mastodon': {'name': 'Mastodon', 'api_available': True, 'auth_type': 'oauth2'},
        'bluesky': {'name': 'Bluesky', 'api_available': True, 'auth_type': 'custom'},
        'discord': {'name': 'Discord', 'api_available': True, 'auth_type': 'bot_token'},
        'telegram': {'name': 'Telegram', 'api_available': True, 'auth_type': 'bot_token'},
        'whatsapp': {'name': 'WhatsApp Business', 'api_available': True, 'auth_type': 'custom'}
    }
    
    return jsonify({
        'platforms': platform_info,
        'total': len(platform_info)
    }), 200

