# -*- coding: utf-8 -*-
import pytest
from datetime import datetime

from quant_engine.state.builders import build_quant_state
from quant_engine.integration.thesis_builder import init_thesis
from quant_engine.integration.tradingagents_adapter import build_quant_context, to_quant_context_string


@pytest.fixture(scope="session")
def state():
    return build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))


@pytest.fixture(scope="session")
def quant_context(state):
    return to_quant_context_string(build_quant_context("SPY", datetime(2024, 6, 3, 23, 59, 59)))


@pytest.fixture(scope="session")
def thesis(state):
    return init_thesis(state, "T+1", "test-run-001", "deepseek",
                       "deepseek-v4-pro", "research_prompt_v1", "quant_analyst_v1")
