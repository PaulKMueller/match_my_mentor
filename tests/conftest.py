import pytest
from src import create_app, db

@pytest.fixture()
def app():
    app = create_app("sqlite://")
    
    with app.app_context():
        db.create_all()

    yield app