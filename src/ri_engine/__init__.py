"""Recursive Intelligence Engine — prompt improvement via Variation → Selection → Retention."""

from ri_engine.api import (
    ImproveResult,
    ObjectiveTooVagueError,
    PlateauImproveResult,
    assess_objective,
    improve,
    improve_template,
    improve_until_plateau,
    list_templates,
)
from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.models import Candidate, GenerationResult, RunConfig

from ri_engine.unix_compound import Session as UnixCompoundSession
from ri_engine.unix_compound import start as compound_start

__all__ = [
    "RecursiveIntelligenceEngine",
    "Candidate",
    "GenerationResult",
    "RunConfig",
    "improve",
    "improve_template",
    "improve_until_plateau",
    "assess_objective",
    "list_templates",
    "ImproveResult",
    "PlateauImproveResult",
    "ObjectiveTooVagueError",
    "UnixCompoundSession",
    "compound_start",
]
__version__ = "0.2.0"
