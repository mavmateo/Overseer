"""Simulation profiles for common oil, gas, and mining assets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalProfile:
    signal_id: str
    unit: str
    base_value: float
    amplitude: float
    sampling_seconds: int


@dataclass(frozen=True)
class AssetProfile:
    asset_id: str
    area_id: str
    equipment_class: str
    signals: tuple[SignalProfile, ...]


ASSET_PROFILES: tuple[AssetProfile, ...] = (
    AssetProfile(
        asset_id="crusher-01",
        area_id="processing",
        equipment_class="crusher",
        signals=(
            SignalProfile("motor_current", "A", 42.0, 6.0, 1),
            SignalProfile("bearing_temp", "C", 78.0, 5.0, 5),
            SignalProfile("vibration_rms", "mm/s", 3.5, 1.2, 1),
        ),
    ),
    AssetProfile(
        asset_id="pump-07",
        area_id="dewatering",
        equipment_class="pump",
        signals=(
            SignalProfile("discharge_pressure", "bar", 14.0, 2.2, 1),
            SignalProfile("flow_rate", "m3/h", 165.0, 18.0, 1),
            SignalProfile("motor_temp", "C", 68.0, 4.0, 5),
        ),
    ),
    AssetProfile(
        asset_id="tank-02",
        area_id="storage",
        equipment_class="tank",
        signals=(
            SignalProfile("level", "%", 63.0, 7.5, 5),
            SignalProfile("temperature", "C", 34.0, 2.0, 5),
            SignalProfile("pressure", "kPa", 152.0, 12.0, 5),
        ),
    ),
    AssetProfile(
        asset_id="gasdet-04",
        area_id="utilities",
        equipment_class="gas-detector",
        signals=(
            SignalProfile("h2s_ppm", "ppm", 2.0, 1.2, 1),
            SignalProfile("co_ppm", "ppm", 3.5, 0.8, 1),
            SignalProfile("battery_pct", "%", 94.0, 0.5, 30),
        ),
    ),
)

