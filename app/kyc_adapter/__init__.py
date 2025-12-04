"""
KYC Adapter Module

Provides abstract base class and concrete implementations for KYC providers.
"""

from .base import KYCProvider
from .shuftipro import ShuftiProAdapter

__all__ = ["KYCProvider", "ShuftiProAdapter"]
