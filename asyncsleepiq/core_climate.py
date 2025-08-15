"""Core climate component handling for SleepIQ beds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .api import SleepIQAPI
from .consts import SIDES_FULL, CoreTemps, Side


CLIMATE_MODE_MAP = {
    "off": CoreTemps.OFF,
    "heating_push_low": CoreTemps.HEATING_PUSH_LOW,
    "heating_push_med": CoreTemps.HEATING_PUSH_MED,
    "heating_push_high": CoreTemps.HEATING_PUSH_HIGH,
    "cooling_pull_low": CoreTemps.COOLING_PULL_LOW,
    "cooling_pull_med": CoreTemps.COOLING_PULL_MED,
    "cooling_pull_high": CoreTemps.COOLING_PULL_HIGH,
}


REVERSE_CLIMATE_MODE_MAP = {v: k for k, v in CLIMATE_MODE_MAP.items()}


@dataclass
class CoreClimateState:
    """State representation for core climate control."""

    mode: Literal[
        "off",
        "heating_push_low",
        "heating_push_med",
        "heating_push_high",
        "cooling_pull_low",
        "cooling_pull_med",
        "cooling_pull_high",
        "unknown",
    ]
    remaining_minutes: int


class SleepIQCoreClimate:
    """Base class for core climate components."""

    max_core_climate_time = 600

    def __init__(self, api: SleepIQAPI, bed_id: str, side: Side, timer: int, temperature: CoreTemps) -> None:
        """Initialize CoreClimate object."""
        self._api = api
        self.bed_id = bed_id
        self.side = side
        self.is_on = temperature != CoreTemps.OFF
        self.timer = timer
        self.temperature = temperature

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"SleepIQCoreClimate[{self.side}]: {'On' if self.is_on else 'Off'}, "
            f"{self.timer}, {self.temperature.name}"
        )

    __repr__ = __str__

    async def turn_on(self, temperature: CoreTemps, time: int) -> None:
        """Turn on core climate mode through API."""
        await self.set_mode(temperature, time)

    async def turn_off(self) -> None:
        """Turn off core climate mode through API."""
        # The API requires a valid time value even if we're turning the climate off
        await self.set_mode(CoreTemps.OFF, 1)

    async def set_mode(self, temperature: CoreTemps, time: int) -> None:
        """Set core climate mode."""
        raise NotImplementedError

    async def update(self, data: dict[str, Any]) -> None:
        """Update core climate state."""
        raise NotImplementedError


class SleepIQClimateCoolCoreClimate(SleepIQCoreClimate):
    """Core climate component for ClimateCool (cooling-only) beds."""

    async def set_mode(self, temperature: CoreTemps, time: int) -> None:
        """Set cooling mode and timer via API."""
        if temperature in {
            CoreTemps.HEATING_PUSH_LOW,
            CoreTemps.HEATING_PUSH_MED,
            CoreTemps.HEATING_PUSH_HIGH,
        }:
            raise ValueError("Heating modes not supported on ClimateCool beds")
        if temperature == CoreTemps.OFF:
            time = 0
        if time < 0:
            time = 0
        if time > self.max_core_climate_time:
            time = self.max_core_climate_time
        args = [SIDES_FULL[self.side].lower(), REVERSE_CLIMATE_MODE_MAP[temperature], str(time)]
        await self._api.bamkey(self.bed_id, "SetClimateMode", args)
        await self.update({})

    async def update(self, data: dict[str, Any]) -> None:
        """Refresh cooling state from API."""
        args = [SIDES_FULL[self.side].lower()]
        resp = await self._api.bamkey(self.bed_id, "GetClimateMode", args)
        parts = resp.split()
        mode = parts[0] if parts else "off"
        self.temperature = CLIMATE_MODE_MAP.get(mode, CoreTemps.OFF)
        self.is_on = self.temperature != CoreTemps.OFF
        self.timer = int(parts[1]) if self.is_on and len(parts) > 1 else 0

