import pytest
from src.optimizer import Optimizer
import pulp
from src.models import Mentor, Mentee
from src import create_app

@pytest.fixture
def app():
    # Create an instance of the Flask app
    app = create_app()
    # Establish an application context before running the tests
    with app.app_context():
        yield app

# Fixture to prepare mock data
@pytest.fixture
def mock_data():
    return {
        "mentees": [1, 2],
        "mentors": [1, 2],
        "timeslots": [101, 102],
        "availability": {
            (1, 101): True,
            (2, 102): True,
        },
        "preferences": {
            (1, 1): 1,
            (2, 2): 2,
            (1, 2): 3,
            (2, 1): 4,
        }
    }

# Mock the database results
class MockQuery:
    def all(self):
        return [
            type('Mentor', (object,), {'id': 'A', 'name': 'Mentor A'}),
            type('Mentor', (object,), {'id': 'B', 'name': 'Mentor B'}),
            type('Mentee', (object,), {'id': '1', 'name': 'Mentee 1'}),
            type('Mentee', (object,), {'id': '2', 'name': 'Mentee 2'}),
        ]

# Mock database calls in Optimizer.get_results
@pytest.fixture
def optimizer(mock_data, monkeypatch, app):
    with app.app_context():
        opt = Optimizer(mock_data)
        monkeypatch.setattr(Mentor, 'query', MockQuery())
        monkeypatch.setattr(Mentee, 'query', MockQuery())
        yield opt

def test_optimization_setup(optimizer, app):
    # Just ensure the problem is setup without raising an exception
    with app.app_context():
        optimizer.solve()
    # If we get here, it means the optimization problem was set up correctly

def test_optimization_validity(optimizer):
    optimizer.solve()
    # Run the validity check included in the Optimizer class
    assert optimizer.check_results()

def test_get_results_format(optimizer):
    optimizer.solve()
    results = optimizer.get_results()
    print(results)
    assert isinstance(results, dict)
    for timeslot, assignments in results.items():
        for assignment in assignments:
            assert set(assignment.keys()) == {'mentee', 'mentor'}
            assert isinstance(assignment['mentee'], int)
            assert isinstance(assignment['mentor'], int)

