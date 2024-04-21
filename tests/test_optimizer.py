import pytest
from src.optimizer import Optimizer
import pulp
from src.models import Mentor, Mentee
from .conftest import app

# Fixture to prepare mock data
@pytest.fixture
def mock_data():
    return {
        "mentees": ['1', '2'],
        "mentors": ['A', 'B'],
        "timeslots": ['09:00-10:00', '10:00-11:00'],
        "availability": {
            ('A', '09:00-10:00'): True,
            ('B', '10:00-11:00'): True,
        },
        "preferences": {
            ('1', 'A'): 1,
            ('2', 'B'): 2,
            ('1', 'B'): 3,
            ('2', 'A'): 4,
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
def optimizer(mock_data, monkeypatch):
    opt = Optimizer(mock_data)
    monkeypatch.setattr(Mentor, 'query', MockQuery())
    monkeypatch.setattr(Mentee, 'query', MockQuery())
    return opt

def test_optimization_setup(optimizer, app):
    # Just ensure the problem is setup without raising an exception
    with app.app_context():
        optimizer.solve()
    # If we get here, it means the optimization problem was set up correctly

def test_optimization_feasibility(optimizer):
    optimizer.solve()
    assert pulp.LpStatus[optimizer.problem.status] == 'Optimal'

def test_optimization_validity(optimizer):
    optimizer.solve()
    # Run the validity check included in the Optimizer class
    assert optimizer.check_results()

def test_get_results_format(optimizer):
    optimizer.solve()
    results = optimizer.get_results()
    assert isinstance(results, dict)
    for timeslot, assignments in results.items():
        for assignment in assignments:
            assert set(assignment.keys()) == {'mentee', 'mentor'}
            assert isinstance(assignment['mentee'], str)
            assert isinstance(assignment['mentor'], str)

