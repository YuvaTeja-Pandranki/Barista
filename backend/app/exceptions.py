"""Exceptions for missing/failed real-time services (weather, mood, coffee profile)."""

from __future__ import annotations


class RealtimeDataUnavailableError(Exception):
    def __init__(self, message: str, service: str = "service") -> None:
        super().__init__(message)
        self.message = message
        self.service = service


class WeatherUnavailableError(RealtimeDataUnavailableError):
    def __init__(self, message: str) -> None:
        super().__init__(message, service="weather")


class MoodInterpretationUnavailableError(RealtimeDataUnavailableError):
    def __init__(self, message: str) -> None:
        super().__init__(message, service="mood")


class CoffeeProfileUnavailableError(RealtimeDataUnavailableError):
    def __init__(self, message: str) -> None:
        super().__init__(message, service="coffee_profile")
