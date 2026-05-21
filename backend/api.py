from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Post
from datetime import datetime
import os
import uuid
from functools import wraps

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def jwt_required_with_file(fn):
    """自定义装饰器，先检查文件再验证JWT"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # 先检查是否有文件
        if 'image' not in request.files:
            # 检查是否是OPTIONS请求
            if request.method == 'OPTIONS':
                return '', 200
            return jsonify({'error': '没有选择文件'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件格式
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式，请上传图片文件'}), 400

        # 验证JWT
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': '未授权访问', 'msg': str(e)}), 401

    return wrapper


@api_bp.route('/api/upload', methods=['POST', 'OPTIONS'])
@jwt_required_with_file
def upload_image():
    """上传图片"""
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        file = request.files['image']

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user_id))
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        filepath = os.path.join(user_folder, filename)
        file.save(filepath)

        image_url = f"/uploads/{current_user_id}/{filename}"

        return jsonify({
            'message': '上传成功',
            'url': image_url,
            'filename': filename
        }), 201

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


# 以下保持原有代码不变
@api_bp.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        user_id = request.args.get('user_id', type=int)

        query = Post.query.filter_by(is_published=True)

        if user_id:
            query = query.filter_by(user_id=user_id)

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        posts = pagination.items

        return jsonify({
            'posts': [post.to_dict() for post in posts],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取文章列表失败: {str(e)}'}), 500


@api_bp.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        post = Post.query.get(post_id)

        if not post:
            return jsonify({'error': '文章不存在'}), 404

        if not post.is_published:
            return jsonify({'error': '文章未发布'}), 404

        return jsonify({'post': post.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': f'获取文章失败: {str(e)}'}), 500


@api_bp.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        data = request.get_json()

        if not all(k in data for k in ('title', 'content')):
            return jsonify({'error': '标题和内容不能为空'}), 400

        title = data['title'].strip()
        content = data['content'].strip()

        if not title or not content:
            return jsonify({'error': '标题和内容不能为空'}), 400

        if len(title) > 200:
            return jsonify({'error': '标题长度不能超过200个字符'}), 400

        post = Post(
            title=title,
            content=content,
            user_id=current_user_id,
            is_published=data.get('is_published', True)
        )

        db.session.add(post)
        db.session.commit()

        return jsonify({'message': '文章创建成功', 'post': post.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'创建文章失败: {str(e)}'}), 500


@api_bp.route('/api/posts/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        post = Post.query.get(post_id)

        if not post:
            return jsonify({'error': '文章不存在'}), 404

        if post.user_id != current_user_id:
            return jsonify({'error': '没有权限修改此文章'}), 403

        data = request.get_json()

        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'error': '标题不能为空'}), 400
            if len(title) > 200:
                return jsonify({'error': '标题长度不能超过200个字符'}), 400
            post.title = title

        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({'error': '内容不能为空'}), 400
            post.content = content

        if 'is_published' in data:
            post.is_published = data['is_published']

        post.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': '文章更新成功', 'post': post.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'更新文章失败: {str(e)}'}), 500


@api_bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        post = Post.query.get(post_id)

        if not post:
            return jsonify({'error': '文章不存在'}), 404

        if post.user_id != current_user_id:
            return jsonify({'error': '没有权限删除此文章'}), 403

        db.session.delete(post)
        db.session.commit()

        return jsonify({'message': '文章删除成功'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除文章失败: {str(e)}'}), 500


@api_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        return jsonify({'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': f'获取用户信息失败: {str(e)}'}), 500


@api_bp.route('/api/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        pagination = Post.query.filter_by(
            user_id=user_id,
            is_published=True
        ).order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        posts = pagination.items

        return jsonify({
            'user': user.to_dict(),
            'posts': [post.to_dict() for post in posts],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取用户文章失败: {str(e)}'}), 500


@api_bp.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200