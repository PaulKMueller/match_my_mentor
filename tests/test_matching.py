from src.data_adapter import prepare_data_for_optimizer
from src.optimizer import Optimizer
import pytest


import os
import sys
topdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(topdir)


def test_empty_data():
    data = prepare_data_for_optimizer([], [], [], [])
    optimizer = Optimizer(data)
    optimizer.solve()
    assert optimizer.x == {}