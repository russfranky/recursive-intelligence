"""Tests for trait parsing from retention lineage."""

from ri_engine.trait_parser import parse_traits


def test_parse_structured_traits():
    text = """
- [TRAIT:constraint_first] Lead with measurable success criteria (evidence: utility=0.92)
- [TRAIT:failure_mode_guards] Block proxy optimization (evidence: selection survival)
"""
    traits = parse_traits(text)
    assert len(traits) == 2
    assert traits[0].normalized_name() == "constraint_first"
    assert "measurable" in traits[0].instruction.lower()
    assert traits[0].evidence == "utility=0.92"


def test_parse_empty_returns_empty():
    assert parse_traits("") == []
    assert parse_traits("   ") == []
