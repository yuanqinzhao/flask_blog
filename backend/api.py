from idlelib.query import Query

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request

from models import Comment
from models import db, User, Post
from datetime import datetime
import os
import uuid
from functools import wraps

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_MESSAGE_EXTENSIONS = {'docx','doc','txt','rtf'}


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_message_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MESSAGE_EXTENSIONS

def jwt_required_with_image_file(fn):
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
        if not allowed_image_file(file.filename):
            return jsonify({'error': '不支持的文件格式，请上传图片文件'}), 400

        # 验证JWT
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': '未授权访问', 'msg': str(e)}), 401

    return wrapper

def jwt_required_with_message_file(fn):
    """自定义装饰器，先检查文件再验证JWT"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # 先检查是否有文件
        if 'message' not in request.files:
            # 检查是否是OPTIONS请求
            if request.method == 'OPTIONS':
                return '', 200
            return jsonify({'error': '没有选择文件'}), 400

        file = request.files['message']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件格式
        if not allowed_message_file(file.filename):
            return jsonify({'error': '不支持的文件格式，请上传图片文件'}), 400

        # 验证JWT
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': '未授权访问', 'msg': str(e)}), 401

    return wrapper

@api_bp.route('/api/uploadmessage',methods=['POST','OPTIONS'])
@jwt_required_with_message_file
def upload_message():
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        file_image = request.files['message']

        ext = file_image.filename.rsplit('.', 1)[1].lower()
        file_messagename = f"{uuid.uuid4().hex}.{ext}"

        user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user_id))
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        file_messagepath = os.path.join(user_folder, file_messagename)
        file_image.save(file_messagepath)
        message_url = f'/uploads/{current_user_id}/{file_messagename}'

        return jsonify({
            'message': '上传成功',
            'url': message_url,
            'filename': file_messagename
        }), 201

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@api_bp.route('/api/upload', methods=['POST', 'OPTIONS'])
@jwt_required_with_image_file
def upload_image():
    """上传图片"""
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        file_image = request.files['image']

        ext = file_image.filename.rsplit('.', 1)[1].lower()
        file_imagename = f"{uuid.uuid4().hex}.{ext}"

        user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user_id))
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        fileimagepath = os.path.join(user_folder, file_imagename)
        file_image.save(fileimagepath)

        image_url = f"/uploads/{current_user_id}/{file_imagename}"

        return jsonify({
            'message': '上传成功',
            'url': image_url,
            'filename': file_imagename
        }), 201

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500



@api_bp.route('/api/posts', methods=['GET']) # 获取文章
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


@api_bp.route('/api/posts/<int:post_id>', methods=['GET']) # 获取文章列表
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

@api_bp.route('/api/posts/<int:post_id>/comments', methods=['GET'])  # 获取评论
def get_comments(post_id):
    try:
        post = Post.query.get(post_id)

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        sort = request.args.get('sort', 'latest')

        query = Comment.query.filter_by(post_id=post_id, parent_id=None)

        if sort == 'oldest':
            query = query.order_by(Comment.created_at.asc())
        elif sort == 'popular':
            query = query.order_by(Comment.replies.count().desc())
        else:
            query = query.order_by(Comment.created_at.desc())

        pagination = query.pagination(page=page, per_page=per_page, error_out=False)
        comments = pagination.items

        return jsonify({
            'comments': [comment.to_dict() for comment in comments],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取评论失败: {str(e)}'}), 500

@api_bp.route('/api/posts/<int:post_id>/comments',methods=['POST']) # 创建评论
@jwt_required()
def create_comment(post_id):
    try:
        current_user_id = get_jwt_identity()
        current_user_id = int(current_user_id)

        post = Post.query.get(post_id)

        if post.user_id != current_user_id:
            return jsonify({'error': '没有权限评论此文章'}), 403

        if not post:
            return jsonify({'error': '文章不存在'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': '数据获取失败'}), 400

        content = data.get('content','').strip()
        parent_id = data.get('parent_id')

        if not content:
            return jsonify({'error': '评论不能为空'}), 400

        if len(content) > 200:
            return jsonify({'error': '评论不能超过200字符'}), 400

        if parent_id:
            parent_comment = Comment.query.get(parent_id)
            if not parent_comment:
                return jsonify({'error': '回复的评论不存在'}), 400
            if parent_comment.post_id != post_id:
                return jsonify({'error': '评论不属于此文章'}), 400

        comment = Comment(
            content = content,
            user_id = current_user_id,
            post_id = post_id,
            parent_id = parent_id
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify({'comment': '评论创建成功','comments':f'{comment}', 'post': post.to_dict()}),201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'评论失败: {str(e)}'}), 500

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