from src.data_adapter import prepare_data_for_optimizer, get_mentor_availability, get_mentee_preferences
from src.optimizer import Optimizer
import pytest


import os
import sys
topdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(topdir)


def test_empty_data():
    data = prepare_data_for_optimizer([], [])
    optimizer = Optimizer(data)
    optimizer.solve()
    assert optimizer.x == {}

def test_get_mentor_availability():
    mentors_timeslots_data = [
        (1, 101, '09:00', '10:00'),
        (2, 102, '10:00', '11:00'),
        (1, 103, '11:00', '12:00')
    ]
    expected_availability = {
        (1, 101): True,
        (2, 102): True,
        (1, 103): True
    }
    availability = get_mentor_availability(mentors_timeslots_data)
    assert availability == expected_availability

def test_get_mentee_preferences():
    mentee_ratings_data = [
        (1, 1, 5),
        (2, 1, 3),
        (1, 2, 4)
    ]
    expected_preferences = {
        (1, 1): 5,
        (2, 1): 3,
        (1, 2): 4
    }
    preferences = get_mentee_preferences(mentee_ratings_data)
    assert preferences == expected_preferences

def test_prepare_data_for_optimizer():
    mentors_timeslots_data = [
        (1, 101, '09:00', '10:00'),
        (2, 102, '10:00', '11:00')
    ]
    mentee_ratings_data = [
        (1, 1, 5),
        (2, 1, 3)
    ]
    expected_data = {
        "mentors": [1, 2],
        "mentees": [1, 2],
        "timeslots": [101, 102],
        "availability": {
            (1, 101): True,
            (2, 102): True,
        },
        "preferences": {
            (1, 1): 5,
            (2, 1): 3,
        }
    }
    data = prepare_data_for_optimizer(mentors_timeslots_data, mentee_ratings_data)
    assert data == expected_data