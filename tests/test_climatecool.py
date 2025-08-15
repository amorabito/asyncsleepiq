import asyncio
import pytest

from asyncsleepiq.bed import SleepIQBed


class DummyAPI:
    def __init__(self, response: str = "") -> None:
        self.response = response
        self.calls: list[tuple[str, str, list[str] | None]] = []

    async def bamkey(self, bed_id: str, key: str, args: list[str] | None = None) -> str:
        self.calls.append((bed_id, key, args))
        return self.response


BED_DATA = {
    "name": "Bed",
    "bedId": "1",
    "macAddress": "00",
    "sleeperLeftId": "L",
    "sleeperRightId": "R",
    "components": [{"productclassification": "CLIMATECOOL", "base": "BASE", "model": "X"}],
}


def test_capability_detection() -> None:
    bed = SleepIQBed(DummyAPI(), BED_DATA)
    assert bed.capabilities.core_climate_cooling_only is True


def test_set_cooling() -> None:
    api = DummyAPI()
    bed = SleepIQBed(api, BED_DATA)
    asyncio.run(bed.foundation.init_core_climates())
    asyncio.run(bed.set_core_climate("left", "cooling_pull_med", 240))
    assert api.calls[-2] == ("1", "SetClimateMode", ["left", "cooling_pull_med", "240"])


def test_stop_cooling() -> None:
    api = DummyAPI()
    bed = SleepIQBed(api, BED_DATA)
    asyncio.run(bed.foundation.init_core_climates())
    asyncio.run(bed.set_core_climate("right", "off", 0))
    assert api.calls[-2] == ("1", "SetClimateMode", ["right", "off", "0"])


def test_clamp_minutes() -> None:
    api = DummyAPI()
    bed = SleepIQBed(api, BED_DATA)
    asyncio.run(bed.foundation.init_core_climates())
    asyncio.run(bed.set_core_climate("left", "cooling_pull_low", 9999))
    assert api.calls[-2] == ("1", "SetClimateMode", ["left", "cooling_pull_low", "600"])


def test_reject_heating() -> None:
    api = DummyAPI()
    bed = SleepIQBed(api, BED_DATA)
    asyncio.run(bed.foundation.init_core_climates())
    with pytest.raises(ValueError):
        asyncio.run(bed.set_core_climate("left", "heating_push_low", 30))


def test_get_state() -> None:
    api = DummyAPI("cooling_pull_med 240")
    bed = SleepIQBed(api, BED_DATA)
    asyncio.run(bed.foundation.init_core_climates())
    state = asyncio.run(bed.get_core_climate("left"))
    assert state.mode == "cooling_pull_med"
    assert state.remaining_minutes == 240
    assert api.calls[-1] == ("1", "GetClimateMode", ["left"])
