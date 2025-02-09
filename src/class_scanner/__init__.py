"""
Class scanner package for game mods
"""

__version__ = "0.1.0"

from .models.core import ClassData, PboClasses
from .scanner import Scanner, ClassScanner

__all__ = [
    'ClassData',
    'PboClasses',
    'Scanner',
    'ClassScanner',
]
