"""
Tests for travel tools and agent logic.
Run with: pytest tests/ -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools.travel_tools import (
    weather_tool,
    attraction_search_tool,
    restaurant_search_tool,
    distance_tool,
    cost_calculator_tool,
    TOOL_REGISTRY,
)


# ---------------------------------------------------------------------------
# Tool tests
# ---------------------------------------------------------------------------
class TestWeatherTool:
    def test_known_city(self):
        result = weather_tool("Đà Nẵng")
        assert "condition" in result
        assert "temp_c" in result
        assert result["location"] == "Đà Nẵng"

    def test_unknown_city(self):
        result = weather_tool("Mars")
        assert "error" in result

    def test_case_insensitive(self):
        r1 = weather_tool("đà nẵng")
        r2 = weather_tool("ĐÀ NẴNG")
        assert r1["temp_c"] == r2["temp_c"]


class TestAttractionTool:
    def test_basic_search(self):
        result = attraction_search_tool("Đà Nẵng")
        assert "attractions" in result
        assert len(result["attractions"]) > 0

    def test_filter_by_interest(self):
        result = attraction_search_tool("Đà Nẵng", interests=["biển"])
        attractions = result["attractions"]
        # Beach should be first
        assert any("biển" in a["type"].lower() or any("biển" in t for t in a["tags"])
                   for a in attractions[:2])

    def test_max_results(self):
        result = attraction_search_tool("Đà Nẵng", max_results=2)
        assert len(result["attractions"]) <= 2

    def test_unknown_city(self):
        result = attraction_search_tool("UnknownCity")
        assert "error" in result


class TestRestaurantTool:
    def test_basic_search(self):
        result = restaurant_search_tool("Đà Nẵng")
        assert "restaurants" in result
        assert len(result["restaurants"]) > 0

    def test_filter_by_cuisine(self):
        result = restaurant_search_tool("Đà Nẵng", cuisine="Hải sản")
        for r in result["restaurants"]:
            assert "hải sản" in r["cuisine"].lower()

    def test_filter_by_budget(self):
        budget = 100_000
        result = restaurant_search_tool("Đà Nẵng", budget_per_person_vnd=budget)
        for r in result["restaurants"]:
            assert r["avg_price_vnd"] <= budget

    def test_rating_sort(self):
        result = restaurant_search_tool("Đà Nẵng")
        ratings = [r["rating"] for r in result["restaurants"]]
        assert ratings == sorted(ratings, reverse=True)


class TestDistanceTool:
    def test_known_route(self):
        result = distance_tool("Đà Nẵng", "Hội An")
        assert "distance_km" in result
        assert result["distance_km"] > 0
        assert "duration_minutes" in result

    def test_unknown_location(self):
        result = distance_tool("Đà Nẵng", "Unknown Place")
        assert "error" in result

    def test_modes(self):
        car = distance_tool("Đà Nẵng", "Hội An", mode="car")
        walk = distance_tool("Đà Nẵng", "Hội An", mode="walking")
        # Same distance, walking takes longer
        assert car["distance_km"] == walk["distance_km"]
        assert walk["duration_minutes"] > car["duration_minutes"]


class TestCostCalculator:
    def test_basic_calculation(self):
        result = cost_calculator_tool(
            num_days=3,
            accommodation_per_night_vnd=500_000,
            meals_per_day_vnd=300_000,
            transport_total_vnd=200_000,
        )
        assert result["num_days"] == 3
        expected = 3 * 500_000 + 3 * 300_000 + 200_000
        assert result["total_vnd"] == expected

    def test_breakdown_keys(self):
        result = cost_calculator_tool(num_days=2)
        assert "breakdown" in result
        for key in ["accommodation", "meals", "transport", "attractions", "other"]:
            assert key in result["breakdown"]

    def test_daily_average(self):
        result = cost_calculator_tool(num_days=4, accommodation_per_night_vnd=400_000,
                                      meals_per_day_vnd=200_000)
        assert result["daily_average_vnd"] == result["total_vnd"] // 4


# ---------------------------------------------------------------------------
# Tool Registry tests
# ---------------------------------------------------------------------------
class TestToolRegistry:
    def test_all_tools_present(self):
        expected = {"weather_tool", "attraction_search_tool", "restaurant_search_tool",
                    "distance_tool", "cost_calculator_tool"}
        assert expected == set(TOOL_REGISTRY.keys())

    def test_all_tools_callable(self):
        for name, meta in TOOL_REGISTRY.items():
            assert callable(meta["fn"]), f"{name} fn is not callable"
            assert isinstance(meta["description"], str)


# ---------------------------------------------------------------------------
# Agent parser tests (no LLM needed)
# ---------------------------------------------------------------------------
class TestAgentParsers:
    def test_parse_action(self):
        from src.agent.agent import _parse_action
        text = 'Action: {"tool": "weather_tool", "args": {"location": "Đà Nẵng"}}'
        result = _parse_action(text)
        assert result is not None
        tool, args = result
        assert tool == "weather_tool"
        assert args["location"] == "Đà Nẵng"

    def test_parse_final_answer(self):
        from src.agent.agent import _parse_final_answer
        text = "Final Answer: Đây là câu trả lời của tôi."
        assert _parse_final_answer(text) == "Đây là câu trả lời của tôi."

    def test_parse_thought(self):
        from src.agent.agent import _parse_thought
        text = "Thought: Tôi cần kiểm tra thời tiết trước.\nAction: ..."
        thought = _parse_thought(text)
        assert thought == "Tôi cần kiểm tra thời tiết trước."
