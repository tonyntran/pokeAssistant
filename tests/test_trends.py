import json
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from pokeassistant.scrapers.trends import (
    parse_interest_over_time,
    fetch_trends,
)
from pokeassistant.models import TrendDataPoint

FIXTURES = Path(__file__).parent / "fixtures"


def _make_mock_dataframe():
    """Build a DataFrame mimicking pytrends interest_over_time() output."""
    data = json.loads((FIXTURES / "trends_interest.json").read_text())
    keyword = "prismatic evolutions"
    dates = list(data[keyword].keys())
    values = list(data[keyword].values())
    is_partial = list(data["isPartial"].values())

    df = pd.DataFrame(
        {keyword: values, "isPartial": is_partial},
        index=pd.to_datetime(dates),
    )
    df.index.name = "date"
    return df


class TestParseInterestOverTime:
    def test_converts_to_trend_data_points(self):
        df = _make_mock_dataframe()
        points = parse_interest_over_time(df, "prismatic evolutions")
        assert len(points) == 5
        assert all(isinstance(p, TrendDataPoint) for p in points)
        assert points[0].keyword == "prismatic evolutions"
        assert points[0].interest == 100
        assert points[0].date == date(2025, 1, 12)
        assert points[0].source == "google_trends"

    def test_skips_partial_data(self):
        df = _make_mock_dataframe()
        points = parse_interest_over_time(df, "prismatic evolutions", skip_partial=True)
        # Last entry is partial, should be skipped
        assert len(points) == 4

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        points = parse_interest_over_time(df, "prismatic evolutions")
        assert points == []


class TestFetchTrends:
    @patch("pytrends.request.TrendReq")
    def test_fetch_returns_data_points(self, mock_trend_req_cls):
        mock_pytrends = MagicMock()
        mock_trend_req_cls.return_value = mock_pytrends
        mock_pytrends.interest_over_time.return_value = _make_mock_dataframe()

        points = fetch_trends(["prismatic evolutions"])
        assert len(points) == 5
        assert points[0].keyword == "prismatic evolutions"
        mock_pytrends.build_payload.assert_called_once()

    @patch("pytrends.request.TrendReq")
    def test_fetch_handles_exception(self, mock_trend_req_cls):
        mock_pytrends = MagicMock()
        mock_trend_req_cls.return_value = mock_pytrends
        mock_pytrends.interest_over_time.side_effect = Exception("Rate limited")

        points = fetch_trends(["prismatic evolutions"])
        assert points == []

    @patch("pytrends.request.TrendReq")
    def test_fetch_multiple_keywords(self, mock_trend_req_cls):
        mock_pytrends = MagicMock()
        mock_trend_req_cls.return_value = mock_pytrends

        # Build a multi-keyword DataFrame
        df = _make_mock_dataframe()
        df["prismatic evolutions ETB"] = [90, 75, 55, 40, 30]
        mock_pytrends.interest_over_time.return_value = df

        points = fetch_trends(["prismatic evolutions", "prismatic evolutions ETB"])
        keywords = {p.keyword for p in points}
        assert "prismatic evolutions" in keywords
        assert "prismatic evolutions ETB" in keywords
