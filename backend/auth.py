# backend/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db, User
import re

auth_bp = Blueprint('auth', __name__)


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    if len(password) < 6:
        return False, "密码长度至少为6个字符"
    return True, ""


@auth_bp.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        if not all(k in data for k in ('username', 'email', 'password')):
            return jsonify({'error': '缺少必填字段'}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']

        if len(username) < 3 or len(username) > 80:
            return jsonify({'error': '用户名长度必须在3-80个字符之间'}), 400

        if not validate_email(email):
            return jsonify({'error': '邮箱格式不正确'}), 400

        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({'error': '邮箱已被注册'}), 409

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # 关键修复：将用户ID转换为字符串
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': '注册成功',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'注册失败: {str(e)}'}), 500


@auth_bp.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        if not all(k in data for k in ('username', 'password')):
            return jsonify({'error': '请输入用户名和密码'}), 400

        username = data['username'].strip()
        password = data['password']
        remember = data.get('remember', False)

        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        if not user or not user.check_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401

        if not user.is_active:
            return jsonify({'error': '账号已被禁用'}), 403

        # 关键修复：将用户ID转换为字符串
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        response_data = {
            'message': '登录成功',
            'user': user.to_dict(),
            'access_token': access_token
        }

        if remember:
            response_data['refresh_token'] = refresh_token

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_jwt_identity()
        # 确保identity是字符串
        access_token = create_access_token(identity=str(current_user_id))

        return jsonify({'access_token': access_token}), 200

    except Exception as e:
        return jsonify({'error': f'令牌刷新失败: {str(e)}'}), 500


@auth_bp.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        current_user_id = get_jwt_identity()
        # 将字符串ID转回整数
        user = User.query.get(int(current_user_id))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        return jsonify({'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': f'获取用户信息失败: {str(e)}'}), 500


@auth_bp.route('/api/user/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        current_user_id = get_jwt_identity()
        # 将字符串ID转回整数
        user = User.query.get(int(current_user_id))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        data = request.get_json()

        if 'email' in data:
            email = data['email'].strip().lower()
            if not validate_email(email):
                return jsonify({'error': '邮箱格式不正确'}), 400

            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': '邮箱已被其他用户使用'}), 409

            user.email = email

        if 'current_password' in data and 'new_password' in data:
            if not user.check_password(data['current_password']):
                return jsonify({'error': '当前密码不正确'}), 400

            is_valid, message = validate_password(data['new_password'])
            if not is_valid:
                return jsonify({'error': message}), 400

            user.set_password(data['new_password'])

        db.session.commit()

        return jsonify({'message': '用户信息更新成功', 'user': user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'更新用户信息失败: {str(e)}'}), 500