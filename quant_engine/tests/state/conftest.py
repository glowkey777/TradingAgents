# -*- coding: utf-8 -*-
import pytest
from datetime import datetime

from quant_engine.state import build_quant_state


@pytest.fixture(scope="session")
def state_2024():
    return build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))


@pytest.fixture(scope="session")
def state_crash():
    return build_quant_state("SPY", datetime(2020, 3, 16, 23, 59, 59))
