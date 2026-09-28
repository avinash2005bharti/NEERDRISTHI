import pytest
from app.gis.spatial_engine import spatial_engine
from app.sandbox.runner import sandbox_runner, SandboxExecutionRequest


@pytest.mark.asyncio
async def test_spatial_engine_intersections():
    # Malabar Point reef test coordinates
    malabar_lon, malabar_lat = 72.78, 18.92
    hits = spatial_engine.check_point_intersections(malabar_lon, malabar_lat)
    assert len(hits) > 0
    assert any("Malabar" in h["name"] for h in hits)

    # Clear open ocean point (safe)
    safe_lon, safe_lat = 72.0, 18.0
    safe_hits = spatial_engine.check_point_intersections(safe_lon, safe_lat)
    assert len(safe_hits) == 0

    # Distance calculation
    dist = spatial_engine.haversine_distance_km((72.82, 18.98), (72.71, 18.98))
    assert 10.0 < dist < 13.0


@pytest.mark.asyncio
async def test_isolated_sandbox_calculation():
    code = """
import json
with open("context.json") as f:
    ctx = json.load(f)

wave = ctx.get("wave_height", 1.2)
wind = ctx.get("wind_speed", 15.0)

# Calculate maritime kinetic sea energy index
energy = 0.5 * 1025 * (wave ** 2) * (wind / 3.6)

with open("output.json", "w") as f:
    json.dump({"kinetic_energy_joules": round(energy, 2), "safe": energy < 10000}, f)

print(f"Computed sea energy: {round(energy, 2)}")
"""
    req = SandboxExecutionRequest(
        code=code,
        context_data={"wave_height": 1.5, "wind_speed": 18.0},
        timeout_seconds=5.0
    )
    result = await sandbox_runner.execute(req)
    assert result.status == "success"
    assert result.result_data is not None
    assert "kinetic_energy_joules" in result.result_data
    assert "Computed sea energy" in result.stdout


@pytest.mark.asyncio
async def test_isolated_sandbox_blocks_network():
    # Attempt to import blocked network module
    code = """
import socket
s = socket.socket()
"""
    req = SandboxExecutionRequest(code=code, timeout_seconds=3.0)
    result = await sandbox_runner.execute(req)
    assert result.status == "error"
    assert "Security Policy" in result.stderr or "ImportError" in result.stderr
