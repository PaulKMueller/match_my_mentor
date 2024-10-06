from flask import Flask
from .models import db  # Keep this at the top

def create_app(database_uri='sqlite:///mentoring.db'):
    app = Flask(__name__)

    # Import the blueprint locally to avoid circular imports
    from .app import main
    app.register_blueprint(main)

    # Set up app configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = "my_secret_key"
    app.config['WTF_CSRF_ENABLED'] = False

    # Initialize database
    db.init_app(app)

    # Create database tables if needed
    with app.app_context():
        db.create_all()

    return app