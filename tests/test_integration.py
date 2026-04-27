import pytest
import asyncio
from core.base_device import BaseDeviceException
from models.config import ChannelConfig, ChannelProperties

@pytest.mark.asyncio
async def test_full_system_integration(connected_system):
    """
    Verifies that the system can discover devices, map channels, 
    and perform read/write operations with scaling.
    """
    system = connected_system
    
    # 1. Verify Discovery
    devices = system.device_manager.get_all_devices()
    assert len(devices) >= 2, "Should have discovered at least mock_1 and mock_2"
    
    # 2. Verify Connection
    mock_1 = system.device_manager.get_device("mock_1")
    assert mock_1.is_connected, "mock_1 should be connected"

    # 3. Inject a test channel for verification (since config might vary)
    ch_id = "ch_temp_test"
    ch_cfg = ChannelConfig(
        channel_id=ch_id,
        device_id="mock_1",
        signal_id="AI0",
        properties=ChannelProperties(unit="C", min=-50, max=150, resolution=0.1, offset=-20)
    )
    system.channel_manager.channels[ch_id] = ch_cfg

    # 4. Test Read with Scaling
    # AI0 starts at 2.5 (Raw)
    # Value = (2.5 * 0.1) + (-20) = 0.25 - 20 = -19.75
    val = await system.channel_manager.read_channel(ch_id)
    assert val == -19.75, f"Expected -19.75, got {val}"

    # 5. Test Write with Scaling
    # Target -19.8 C
    # Raw = (-19.8 - (-20)) / 0.1 = 0.2 / 0.1 = 2.0
    await system.channel_manager.write_channel(ch_id, -19.8)
    
    # Verify raw signal on device
    raw_sig_val = mock_1.read_signal("AI0")
    assert raw_sig_val == pytest.approx(2.0), f"Expected raw value 2.0, got {raw_sig_val}"

    # 6. Test Out of Bounds (Channel Level)
    with pytest.raises(ValueError) as excinfo:
        await system.channel_manager.write_channel(ch_id, 200.0)
    assert "out of bounds for channel" in str(excinfo.value)

    # 7. Test Out of Bounds (Signal Level - Dual Layer)
    # AI0 max is 5.0
    # Let's use a channel that allows high values
    ch_cfg_high = ChannelConfig(
        channel_id="ch_high",
        device_id="mock_1",
        signal_id="AI0",
        properties=ChannelProperties(unit="V", min=0, max=100, resolution=1.0, offset=0)
    )
    system.channel_manager.channels["ch_high"] = ch_cfg_high
    
    with pytest.raises(BaseDeviceException) as excinfo:
        await system.channel_manager.write_channel("ch_high", 10.0) # Raw 10.0 > 5.0
    assert excinfo.value.code == "SIGNAL_OUT_OF_BOUNDS"
