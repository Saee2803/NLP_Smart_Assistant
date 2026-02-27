# anomaly/__init__.py
"""
Anomaly Detection Module

Provides statistical anomaly detection for metrics using z-score method.
"""

from anomaly.detector import AnomalyDetector

__all__ = ['AnomalyDetector']
