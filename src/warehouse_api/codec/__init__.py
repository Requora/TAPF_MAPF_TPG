"""Public API for the codec module."""
from ._json import dumps, from_data, loads, to_data

__all__ = ['dumps', 'from_data', 'loads', 'to_data']
