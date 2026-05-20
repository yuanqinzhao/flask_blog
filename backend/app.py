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

    # CORS配置
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config["MAX_PICTURE_LENGTH"] = 16 * 1024 * 1024

    #确保目录存在
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    # 提供上传文件的访问
    @app.route('/upload/<filename>')
    def upload_pictures(filename):
        return send_from_dictory(app.config['UPLOAD_FOLDER'],filename)

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