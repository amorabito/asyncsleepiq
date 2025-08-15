"""Bed object from SleepIQ API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .api import SleepIQAPI
from .consts import SIDES_FULL, Side
from .core_climate import (
    CoreClimateState,
    SleepIQCoreClimate,
    CLIMATE_MODE_MAP,
    REVERSE_CLIMATE_MODE_MAP,
)
from .foundation import SleepIQFoundation
from .sleeper import SleepIQSleeper


@dataclass
class BedCapabilities:
    """Available capabilities for a bed."""

    core_climate_cooling_only: bool = False




class SleepIQBed:
    """Bed object from SleepIQ API."""

    def __init__(self, api: SleepIQAPI, data: dict[str, Any]) -> None:
        """Initialize bed object."""
        self._api = api

        self.name = data["name"]
        self.id = data["bedId"]
        self.mac_addr = data["macAddress"]
        self.paused = False
        self.sleepers = [
            SleepIQSleeper(api, self.id, data[f"sleeper{SIDES_FULL[side]}Id"], side)
            for side in [Side.LEFT, Side.RIGHT]
            if data.get(f"sleeper{SIDES_FULL[side]}Id")
        ]
        self.foundation = SleepIQFoundation(api, self.id)
        self.capabilities = BedCapabilities()

        self.model = "Unknown"
        if "model" in data:
            self.model = data["model"]
        elif "components" in data:
            for comp in data["components"]:
                if comp.get("base") == "BASE" and comp.get("model"):
                    self.model = comp["model"]
                if comp.get("productclassification") == "CLIMATECOOL" or comp.get("model") == "CLIMATECOOL":
                    self.capabilities.core_climate_cooling_only = True
        if self.capabilities.core_climate_cooling_only:
            self.foundation.core_climate_cooling_only = True

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"SleepIQBed({self.name}, model={self.model}, id={self.id}) "
            + str(self.sleepers)
            + " "
            + str(self.foundation)
        )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SleepIQBed({self.name}, model={self.model}, id={self.id}) "
            + str(self.sleepers)
            + " "
            + str(self.foundation)
        )

    async def valid(self) -> bool:
        return await self._api.check("bed/" + self.id + "/pauseMode")

    async def calibrate(self) -> None:
        """Calibrate or "baseline" bed."""
        for sleeper in self.sleepers:
            if sleeper.sleeper_id:
                await sleeper.calibrate()
                break

    async def stop_pump(self) -> None:
        """Stop pump."""
        await self._api.put("bed/" + self.id + "/pump/forceIdle")

    async def fetch_pause_mode(self) -> None:
        """Update paused attribute with data from API."""
        json = await self._api.get("bed/" + self.id + "/pauseMode")
        self.paused = json.get("pauseMode", "") == "on"

    async def set_pause_mode(self, mode: bool) -> None:
        """Set pause mode in API and locally."""
        params = {"mode": "on" if mode else "off"}
        await self._api.put("bed/" + self.id + "/pauseMode", params=params)
        self.paused = mode

    async def get_core_climate(self, side: Literal["left", "right"]) -> CoreClimateState:
        """Get current core climate state for a side."""
        side_enum = Side.LEFT if side == "left" else Side.RIGHT
        core = next((c for c in self.foundation.core_climates if c.side == side_enum), None)
        if not core:
            raise ValueError("Core climate not supported")
        await core.update({})
        mode = REVERSE_CLIMATE_MODE_MAP.get(core.temperature, "unknown")
        minutes = core.timer if core.is_on else 0
        return CoreClimateState(mode, minutes)

    async def set_core_climate(
        self,
        side: Literal["left", "right"],
        mode: Literal[
            "off",
            "heating_push_low",
            "heating_push_med",
            "heating_push_high",
            "cooling_pull_low",
            "cooling_pull_med",
            "cooling_pull_high",
        ],
        minutes: int,
    ) -> None:
        """Set core climate for a side."""
        if mode not in CLIMATE_MODE_MAP:
            raise ValueError("Invalid core climate mode")
        if self.capabilities.core_climate_cooling_only and mode.startswith("heating"):
            raise ValueError("Heating not supported on this bed")
        side_enum = Side.LEFT if side == "left" else Side.RIGHT
        minutes = max(0, min(minutes, SleepIQCoreClimate.max_core_climate_time))
        core = next((c for c in self.foundation.core_climates if c.side == side_enum), None)
        if not core:
            raise ValueError("Core climate not supported on this side")
        await core.set_mode(CLIMATE_MODE_MAP[mode], minutes)
