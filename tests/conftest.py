import sys
from pathlib import Path

import pytest

# Make the project root importable when running `pytest` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_groups():
    return [
        [{"title": "Fed raises rates", "source": "Reuters",
          "content": "c1", "description": "d1"}],
        [{"title": "Stock market dips", "source": "AP",
          "content": "c2", "description": "d2"}],
        [{"title": "Tech layoffs continue", "source": "CNBC",
          "content": "c3", "description": "d3"}],
    ]


@pytest.fixture
def reasoner(sample_groups):
    from reasoner import Reasoner
    return Reasoner(sample_groups, topic="economy", intent="interest rates")
