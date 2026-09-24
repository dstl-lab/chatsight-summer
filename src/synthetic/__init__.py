"""Synthetic cohorts for exercising analytics without real student data."""

from src.synthetic.cohort import generate_cohort
from src.synthetic.config import CohortConfig

__all__ = ["CohortConfig", "generate_cohort"]
