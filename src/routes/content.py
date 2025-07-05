from flask import Blueprint, request, jsonify, session
from src.models.content_post import ContentPost, PostDistribution, db
from src.models.social_account import SocialMediaAccount
from src.models.media_file import MediaFile
from src.routes.auth import require_auth
from datetime import datetime
import json

content_bp = Blueprint('content', __name__)

@content_bp.route('/posts', methods=['GET'])
@require_auth
def get_posts():
    """Get all posts for the current user"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        query = ContentPost.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        posts = query.order_by(ContentPost.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'posts': [post.to_dict() for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch posts: {str(e)}'}), 500

@content_bp.route('/posts', methods=['POST'])
@require_auth
def create_post():
    """Create a new content post"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        user_id = session.get('user_id')
        
        # Create new post
        new_post = ContentPost(
            user_id=user_id,
            title=data.get('title', ''),
            content=content,
            content_type=data.get('content_type', 'text'),
            status=data.get('status', 'draft')
        )
        
        # Set media attachments if provided
        if 'media_attachments' in data:
            new_post.set_media_attachments(data['media_attachments'])
        
        # Set hashtags if provided
        if 'hashtags' in data:
            new_post.set_hashtags(data['hashtags'])
        
        # Set mentions if provided
        if 'mentions' in data:
            new_post.set_mentions(data['mentions'])
        
        # Set platform-specific content if provided
        if 'platform_content' in data:
            new_post.set_platform_content(data['platform_content'])
        
        # Set scheduled time if provided
        if 'scheduled_for' in data and data['scheduled_for']:
            try:
                new_post.scheduled_for = datetime.fromisoformat(data['scheduled_for'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid scheduled_for format. Use ISO format.'}), 400
        
        db.session.add(new_post)
        db.session.commit()
        
        return jsonify({
            'message': 'Post created successfully',
            'post': new_post.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create post: {str(e)}'}), 500

@content_bp.route('/posts/<int:post_id>', methods=['GET'])
@require_auth
def get_post(post_id):
    """Get a specific post"""
    try:
        user_id = session.get('user_id')
        post = ContentPost.query.filter_by(id=post_id, user_id=user_id).first()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        return jsonify({'post': post.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch post: {str(e)}'}), 500

@content_bp.route('/posts/<int:post_id>', methods=['PUT'])
@require_auth
def update_post(post_id):
    """Update a post"""
    try:
        user_id = session.get('user_id')
        post = ContentPost.query.filter_by(id=post_id, user_id=user_id).first()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update basic fields
        if 'title' in data:
            post.title = data['title']
        if 'content' in data:
            post.content = data['content']
        if 'content_type' in data:
            post.content_type = data['content_type']
        if 'status' in data:
            post.status = data['status']
        
        # Update media attachments if provided
        if 'media_attachments' in data:
            post.set_media_attachments(data['media_attachments'])
        
        # Update hashtags if provided
        if 'hashtags' in data:
            post.set_hashtags(data['hashtags'])
        
        # Update mentions if provided
        if 'mentions' in data:
            post.set_mentions(data['mentions'])
        
        # Update platform-specific content if provided
        if 'platform_content' in data:
            post.set_platform_content(data['platform_content'])
        
        # Update scheduled time if provided
        if 'scheduled_for' in data:
            if data['scheduled_for']:
                try:
                    post.scheduled_for = datetime.fromisoformat(data['scheduled_for'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'Invalid scheduled_for format. Use ISO format.'}), 400
            else:
                post.scheduled_for = None
        
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Post updated successfully',
            'post': post.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update post: {str(e)}'}), 500

@content_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@require_auth
def delete_post(post_id):
    """Delete a post"""
    try:
        user_id = session.get('user_id')
        post = ContentPost.query.filter_by(id=post_id, user_id=user_id).first()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Delete associated distributions
        PostDistribution.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({'message': 'Post deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete post: {str(e)}'}), 500

@content_bp.route('/posts/<int:post_id>/publish', methods=['POST'])
@require_auth
def publish_post(post_id):
    """Publish a post to selected social media platforms"""
    try:
        user_id = session.get('user_id')
        post = ContentPost.query.filter_by(id=post_id, user_id=user_id).first()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        data = request.get_json()
        platform_ids = data.get('platform_ids', []) if data else []
        
        if not platform_ids:
            return jsonify({'error': 'No platforms selected'}), 400
        
        # Get user's social media accounts for selected platforms
        accounts = SocialMediaAccount.query.filter(
            SocialMediaAccount.user_id == user_id,
            SocialMediaAccount.id.in_(platform_ids),
            SocialMediaAccount.connection_status == 'active'
        ).all()
        
        if not accounts:
            return jsonify({'error': 'No active accounts found for selected platforms'}), 400
        
        distributions = []
        
        # Create distribution records for each platform
        for account in accounts:
            distribution = PostDistribution(
                post_id=post_id,
                social_media_account_id=account.id,
                distribution_status='pending',
                scheduled_for=post.scheduled_for or datetime.utcnow()
            )
            db.session.add(distribution)
            distributions.append(distribution)
        
        # Update post status
        post.status = 'scheduled' if post.scheduled_for else 'publishing'
        post.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # TODO: Trigger actual publishing process here
        # This would involve calling the appropriate API integration services
        
        return jsonify({
            'message': f'Post scheduled for publishing to {len(accounts)} platforms',
            'distributions': [dist.to_dict() for dist in distributions]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to publish post: {str(e)}'}), 500

@content_bp.route('/posts/<int:post_id>/distributions', methods=['GET'])
@require_auth
def get_post_distributions(post_id):
    """Get distribution status for a post"""
    try:
        user_id = session.get('user_id')
        post = ContentPost.query.filter_by(id=post_id, user_id=user_id).first()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        distributions = PostDistribution.query.filter_by(post_id=post_id).all()
        
        return jsonify({
            'distributions': [dist.to_dict() for dist in distributions],
            'total': len(distributions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch distributions: {str(e)}'}), 500

@content_bp.route('/distributions/<int:distribution_id>/retry', methods=['POST'])
@require_auth
def retry_distribution(distribution_id):
    """Retry a failed distribution"""
    try:
        user_id = session.get('user_id')
        
        # Get distribution and verify ownership
        distribution = db.session.query(PostDistribution).join(ContentPost).filter(
            PostDistribution.id == distribution_id,
            ContentPost.user_id == user_id
        ).first()
        
        if not distribution:
            return jsonify({'error': 'Distribution not found'}), 404
        
        if distribution.distribution_status not in ['failed', 'error']:
            return jsonify({'error': 'Can only retry failed distributions'}), 400
        
        # Reset distribution for retry
        distribution.distribution_status = 'pending'
        distribution.attempted_at = None
        distribution.error_message = None
        distribution.retry_count += 1
        distribution.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # TODO: Trigger retry process here
        
        return jsonify({
            'message': 'Distribution retry initiated',
            'distribution': distribution.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to retry distribution: {str(e)}'}), 500

