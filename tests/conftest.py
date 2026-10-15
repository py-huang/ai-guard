from __future__ import annotations

import os

os.environ.setdefault("IMAGE_FORBID_VISION", "0")

import pytest

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.vault.memory import InMemorySessionVault


@pytest.fixture
def vault() -> InMemorySessionVault:
    return InMemorySessionVault()


@pytest.fixture
def gateway(vault: InMemorySessionVault) -> AISafetyGateway:
    return AISafetyGateway(vault=vault)
