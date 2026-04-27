import pytest
import os
import sys
import asyncio

# Add source directory to path
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if source_path not in sys.path:
    sys.path.append(source_path)

from core.system import SDTBSystem

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def sdtb_system():
    """Fixture to provide a running SDTBSystem instance."""
    config_dir = os.path.join(source_path, "config")
    system = SDTBSystem(config_dir)
    await system.startup()
    
    yield system
    
    await system.shutdown()

@pytest.fixture
async def connected_system(sdtb_system):
    """Fixture that ensures all devices are connected before the test."""
    await sdtb_system.device_manager.connect_all()
    yield sdtb_system
    # We don't disconnect after every test to save time, 
    # but session shutdown will handle it.
