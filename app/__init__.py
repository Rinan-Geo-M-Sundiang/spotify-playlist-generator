from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate  # ✅ Import Migrate
from config import Config

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()  # ✅ Initialize Migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)  # ✅ Attach Migrate to Flask & DB

    from app.routes import api_bp
    app.register_blueprint(api_bp)

    return app
