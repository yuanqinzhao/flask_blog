# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db
from auth import auth_bp
from api import api_bp
from config import config
import os


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    db.init_app(app)
    jwt = JWTManager(app)

    # 在 create_app 函数中找到 CORS 配置部分
    allowed_origins = [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'https://sputter-backtalk-next.ngrok-free.dev',
        'https://blog-frontend-abc123.vercel.app',  # 替换为你的实际域名
    ]

    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    @jwt.unauthorized_loader
    def unauthorized_response(callback):
        return jsonify({'error': '未授权访问', 'msg': '请先登录'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': '无效的Token', 'msg': str(error)}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token已过期', 'msg': '请重新登录'}), 401

    @app.errorhandler(404)
    def not_found(error):
        return {'error': '资源不存在'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': '服务器内部错误'}, 500

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)