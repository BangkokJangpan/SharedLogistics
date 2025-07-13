import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

# SQLAlchemy 1.4 호환성을 위한 Base 클래스
class Base:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "laem-chabang-logistics-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///shared_logistics.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {'pool_pre_ping': True, "pool_recycle": 300}
db = SQLAlchemy(app, model_class=Base)

 