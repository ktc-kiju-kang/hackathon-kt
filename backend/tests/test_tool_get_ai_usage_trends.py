import asyncio
import json

import pytest

from app.agent.tools.get_ai_usage_trends import Input, run


def test_returns_summary_with_source():
    data = json.loads(asyncio.run(run(Input(country="KR", months=23))))
    assert data["country"] == "KR" and data["period"]["from"] == "2024-07"
    assert data["source"].startswith("OpenAI Signals")


def test_unknown_country_raises_readable_error():
    with pytest.raises(ValueError, match="국가"):
        asyncio.run(run(Input(country="ZZ")))


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        Input(country="korea")
    with pytest.raises(ValueError):
        Input(months=24)
