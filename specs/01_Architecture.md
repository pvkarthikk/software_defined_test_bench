# 01_Architecture.md - High-Level Design and Component Layers

## Overview

The Virtual Test Engineer is a software-defined test bench platform designed for automotive ECU (Electronic Control Unit) testing and validation. It provides a REST API for controlling hardware interfaces, executing test scenarios, and collecting sensor data in a configuration-driven, extensible architecture.

## Core Philosophy

- **Software-Defined**: Hardware behavior is defined through configuration files, not hardcoded logic
- **Extensible**: Plugin architecture allows adding new device types without modifying core code
- **Layered Control**: Supports both low-level device commands and high-level test sequences
- **Configuration-Driven**: Test bench setup via YAML/JSON files enables easy reconfiguration for different DUTs

## System Context Diagram

```mermaid
graph TD
    Agent["Test Agent<br/>(HTTP Client)"]
    WebApp["Web Dashboard<br/>(Optional)"]
    VTE["Virtual Test Engineer<br/>REST API + WebSocket"]
    ECU["Physical ECU/DUT<br/>Hardware"]
    Config["YAML/JSON<br/>Configuration"]
    Firmware["Firmware<br/>Files"]
    
    Agent -->|"REST API Calls"| VTE
    WebApp -->|"REST API Calls"| VTE
    VTE -->|"Hardware Control"| ECU
    ECU -->|"Sensor Data"| VTE
    Config -->|"Load Config"| VTE
    Firmware -->|"Flash Firmware"| VTE
    VTE -->|"Program Device"| ECU
    
    style VTE fill:#4A90E2,stroke:#333,stroke-width:3px,color:#fff
    style Agent fill:#E8F0F7,stroke:#333,stroke-width:2px
    style WebApp fill:#E8F0F7,stroke:#333,stroke-width:2px
    style ECU fill:#F5A623,stroke:#333,stroke-width:2px
    style Config fill:#E8F0F7,stroke:#333,stroke-width:2px
    style Firmware fill:#E8F0F7,stroke:#333,stroke-width:2px
```

## Component Architecture

### 1. Hardware Abstraction Layer (HAL)
- **Purpose**: Abstracts physical hardware interfaces from application logic
- **Components**:
  - GPIO Controller: Digital I/O management
  - ADC/DAC Interface: Analog signal handling
  - CAN Transceiver: Automotive network communication
  - PWM Controller: Timing and pulse-width modulation
- **Dual-File Architecture**: Separate interface definitions and implementations

### 2. Device Manager
- **Purpose**: Manages device lifecycle and plugin loading
- **Responsibilities**:
  - Plugin discovery and loading from `/drivers/plugins/`
  - Device initialization and calibration
  - Channel mapping and validation
  - Resource allocation and conflict resolution

### 3. Test Execution Engine
- **Purpose**: Orchestrates test scenario execution
- **Features**:
  - Step-by-step scenario execution
  - Conditional logic and branching
  - Sensor data collection and logging
  - Artifact generation (CSV, logs, screenshots)
  - Both synchronous and asynchronous execution modes

### 4. REST API Layer
- **Purpose**: Provides HTTP interface for external agents
- **Capabilities**:
  - Discovery endpoints for capabilities and status
  - Channel control for I/O operations
  - Scenario management and execution
  - Real-time streaming via WebSocket
  - Configuration validation and loading
### Layered Architecture Diagram

```mermaid
graph TD
    Client["External Agent<br/>Test Client"]
    
    subgraph API["Layer 5: REST API"]
        endpoints["HTTP Endpoints<br/>Channels, Tests, Flashing"]
        websocket["WebSocket<br/>Real-time Streaming"]
    end
    
    subgraph FlashManager["Layer 4: Flashing Manager"]
        flash["Firmware Programming<br/>Protocol Handlers"]
    end
    
    subgraph TestEngine["Layer 3: Test Execution Engine"]
        executor["Scenario Executor<br/>Step Orchestration"]
        logger["Data Logger<br/>CSV/Artifacts"]
    end
    
    subgraph DevManager["Layer 2: Device Manager"]
        discover["Channel/Bus Discovery"]
        state["State Management"]
        resources["Resource Allocation"]
    end
    
    subgraph HAL["Layer 1: Hardware Abstraction Layer"]
        gpio["GPIO Driver"]
        can["CAN Driver"]
        analog["Analog Driver"]
        plugins["Plugin System"]
    end
    
    ECU["Physical Hardware<br/>ECU/DUT"]
    
    Client -->|"REST Calls"| endpoints
    Client -->|"WebSocket"| websocket
    endpoints --> executor
    endpoints --> discover
    endpoints --> flash
    executor --> discover
    executor --> logger
    discover --> state
    state --> resources
    resources --> gpio
    resources --> can
    resources --> analog
    plugins --> gpio
    plugins --> can
    plugins --> analog
    gpio --> ECU
    can --> ECU
    analog --> ECU
    ECU -->|"Sensor Data"| analog
    
    style API fill:#4A90E2,stroke:#333,stroke-width:2px,color:#fff
    style FlashManager fill:#50E3C2,stroke:#333,stroke-width:2px,color:#fff
    style TestEngine fill:#F8E71C,stroke:#333,stroke-width:2px,color:#000
    style DevManager fill:#B8E986,stroke:#333,stroke-width:2px,color:#000
    style HAL fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style ECU fill:#F5A623,stroke:#333,stroke-width:3px
```
## Plugin Architecture

### Plugin Discovery
- Plugins are stored in `/drivers/plugins/` directory
- Each plugin is a Python module with a driver class implementing `PluginInterface`
- Automatic discovery and loading at startup via filesystem scanning
- No manifest files required - discovery based on class attributes

### Plugin Interface Contract
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class PluginInterface(ABC):
    """Abstract base class for all test bench plugins."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration parameters."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up plugin resources and close connections."""
        pass

    @abstractmethod
    def create_channel(self, channel_config: Dict[str, Any]) -> Optional[Channel]:
        """Create a channel instance for the specified configuration."""
        pass

    @abstractmethod
    def create_bus(self, bus_config: Dict[str, Any]) -> Optional[Bus]:
        """Create a bus instance for the specified configuration."""
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Return the plugin type identifier."""
        pass

    @property
    @abstractmethod
    def supported_channel_types(self) -> List[str]:
        """Return list of supported channel types."""
        pass

    @property
    @abstractmethod
    def supported_bus_types(self) -> List[str]:
        """Return list of supported bus types."""
        pass
```

### Supported Plugin Types
- **GPIO Plugin**: Digital I/O control with PWM support
- **Analog Plugin**: ADC/DAC operations with scaling
- **CAN Plugin**: Network message handling with streaming
- **Custom Plugins**: User-defined device types via plugin interface

### Plugin Integration Component Diagram

```mermaid
graph TD
    PM["PluginManager<br/>(Core Component)"]
    FS["File System Scanner<br/>/drivers/plugins/"]
    PI["PluginInterface<br/>(Abstract Base)"]
    
    subgraph GPIO["GPIO Plugin"]
        GPIO_DRV["gpio_driver.py<br/>PluginInterface impl"]
        GPIO_CH["Channel: Digital I/O<br/>PWM"]
    end
    
    subgraph ANALOG["Analog Plugin"]
        ANALOG_DRV["analog_driver.py<br/>PluginInterface impl"]
        ANALOG_CH["Channel: ADC/DAC<br/>Scaling"]
    end
    
    subgraph CAN["CAN Plugin"]
        CAN_DRV["can_driver.py<br/>PluginInterface impl"]
        CAN_BS["Bus: CAN Network<br/>Message Streaming"]
    end
    
    subgraph CUSTOM["Custom Plugin"]
        CUSTOM_DRV["custom_driver.py<br/>PluginInterface impl"]
        CUSTOM_CH["Channel/Bus<br/>User-defined"]
    end
    
    DM["Device Manager"]
    
    FS -->|"Scan for drivers"| PM
    PM -->|"Load & Instantiate"| PI
    PI --> GPIO_DRV
    PI --> ANALOG_DRV
    PI --> CAN_DRV
    PI --> CUSTOM_DRV
    GPIO_DRV --> GPIO_CH
    ANALOG_DRV --> ANALOG_CH
    CAN_DRV --> CAN_BS
    CUSTOM_DRV --> CUSTOM_CH
    PM -->|"Register channels/buses"| DM
    GPIO_CH --> DM
    ANALOG_CH --> DM
    CAN_BS --> DM
    CUSTOM_CH --> DM
    
    style PM fill:#4A90E2,stroke:#333,stroke-width:2px,color:#fff
    style PI fill:#B8E986,stroke:#333,stroke-width:2px
    style GPIO fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style ANALOG fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style CAN fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style CUSTOM fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style DM fill:#F8E71C,stroke:#333,stroke-width:2px
```

## Configuration Lifecycle

1. **Load**: Parse YAML configuration files using PyYAML
2. **Validate**: Check plugin availability, resource conflicts, and schema validation
3. **Initialize**: Load plugins dynamically and create device instances
4. **Calibrate**: Apply scaling factors and limits from configuration
5. **Execute**: Run test scenarios with async execution and real-time monitoring

## Data Flow

```
Agent Request → FastAPI Routes → Test Engine → Device Manager → Plugin → Hardware
                                      ↓
Sensor Data ← Plugin ← Device Manager ← Test Engine ← FastAPI ← Agent Response
                                      ↓
WebSocket Streaming ← Real-time Updates
```

## State Management

- **Test Bench State**: idle, configuring, running, error, shutdown
- **Channel State**: cached values with timestamps, last read/write times
- **Execution State**: scenario progress, step results, artifacts, error tracking
- **Plugin State**: loaded, initialized, error states with recovery options

## Security Considerations

- Input validation using Pydantic models on all API endpoints
- Configuration file integrity checks with schema validation
- Resource limits to prevent hardware damage (configurable ranges)
- Optional authentication for multi-user deployments (extensible)
- CORS support for web-based agents

## Performance Characteristics

- **Latency**: <5ms for channel operations (async I/O)
- **Throughput**: 1000+ CAN messages/second with streaming
- **Concurrent Channels**: Up to 128 digital + 16 analog (configurable)
- **Logging Rate**: Configurable, up to 1000 samples/second with CSV export
- **Memory Usage**: ~50MB base + 10MB per active plugin
- **CPU Usage**: <5% for typical test scenarios