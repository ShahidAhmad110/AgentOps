from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from scripts.health_check import check_health


@pytest.mark.asyncio
async def test_health_check_script_success() -> None:
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 1
    mock_conn.execute.return_value = mock_res
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    with patch("scripts.health_check.engine", mock_engine):
        assert await check_health() is True


@pytest.mark.asyncio
async def test_health_check_script_failure() -> None:
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")

    with patch("scripts.health_check.engine", mock_engine):
        assert await check_health() is False
