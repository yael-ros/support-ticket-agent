import pytest

from support_agent.data.load_tickets import normalize_category, normalize_urgency
from support_agent.schemas import Category, Urgency


def test_normalize_category_known_value():
    assert normalize_category("Technical Support") == Category.TECHNICAL_SUPPORT
    assert normalize_category("Human Resources") == Category.HUMAN_RESOURCES


def test_normalize_category_unknown_value_routes_to_general_inquiry():
    counter: dict[str, int] = {}
    result = normalize_category("Pets & Animals/Veterinary Care", unknown_counter=counter)
    assert result == Category.GENERAL_INQUIRY
    assert counter == {"Pets & Animals/Veterinary Care": 1}


def test_normalize_category_null_routes_to_general_inquiry():
    counter: dict[str, int] = {}
    result = normalize_category(None, unknown_counter=counter)
    assert result == Category.GENERAL_INQUIRY
    assert counter == {"<null>": 1}


def test_normalize_urgency_known_values():
    assert normalize_urgency("low") == Urgency.LOW
    assert normalize_urgency("very_low") == Urgency.LOW
    assert normalize_urgency("medium") == Urgency.MEDIUM
    assert normalize_urgency("high") == Urgency.HIGH
    assert normalize_urgency("critical") == Urgency.CRITICAL


def test_normalize_urgency_unknown_value_raises():
    with pytest.raises(ValueError, match="Unrecognized priority"):
        normalize_urgency("urgent-ish")
