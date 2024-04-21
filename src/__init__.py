from flask import Flask

from .models import db
from .data_adapter import prepare_data_for_optimizer
from .optimizer import Optimizer
from .app import main

def create_app(database_uri='sqlite:///mentoring.db'):
    app = Flask(__name__)

    app.register_blueprint(main)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = "my_secret_key"
    app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        data = prepare_data_for_optimizer()
        # print(data)
        optimizer = Optimizer(data)
        optimizer.solve()

    return app