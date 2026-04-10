# 01_Architecture.md - High-Level Design and Component Layers

## Overview

The Virtual Test Engineer is a software-defined test bench platform designed for automotive ECU (Electronic Control Unit) testing and validation. It provides a REST API for controlling hardware interfaces, executing test scenarios, and collecting sensor data in a configuration-driven, extensible architecture.

## Core Philosophy

- **Software-Defined**: Hardware behavior is defined through configuration files, not hardcoded logic
- **Extensible**: Plugin architecture allows adding new device types without modifying core code
- **Layered Control**: Supports both low-level device commands and high-level test sequences
- **Configuration-Driven**: Test bench setup via YAML/JSON files enables easy reconfiguration for different DUTs

## System Context & Detailed Layered Architecture Diagram

```mermaid
graph TD
    Client1["Test Agent<br/>REST Client"]
    Client2["Web Dashboard<br/>WebSocket Client"]
    
    subgraph API["Layer 5: REST API & Gateway"]
        CH_EP["Channel Endpoints<br/>/channels/{id}<br/>read/write/stream"]
        TEST_EP["Test Endpoints<br/>/runs<br/>start/stop/status"]
        FLASH_EP["Flash Endpoints<br/>/flash<br/>upload/flash/verify"]
        HEALTH_EP["Health/Discovery<br/>/health /config<br/>capabilities"]
        WS["WebSocket Server<br/>Real-time Streams<br/>Event Broadcasting"]
        CORS["CORS & Auth<br/>Rate Limiting"]
    end
    
    subgraph FlashManager["Layer 4: Flashing Manager"]
        PROG["Protocol Handler<br/>UART, JTAG, SPI"]
        VERIFY["Verification<br/>Checksum, Readback"]
        RECOVER["Recovery Logic<br/>Error Handling"]
    end
    
    subgraph TestEngine["Layer 3: Test Execution Engine"]
        EXECUTOR["Scenario Executor<br/>Step Parser<br/>Conditional Logic"]
        STATE_MACHINE["State Machine<br/>idle, running<br/>paused, error"]
        DATA_LOGGER["Data Logger<br/>CSV Writer<br/>Artifact Generator"]
        VALIDATOR["Validator<br/>Assertions<br/>Range Checks"]
    end
    
    subgraph DevManager["Layer 2: Device Manager"]
        DISCOVERY["Discovery Engine<br/>Plugin Scanner<br/>Channel Registry"]
        CHANNEL_MGR["Channel Manager<br/>Read/Write Ops<br/>Caching"]
        BUS_MGR["Bus Manager<br/>Message Routing<br/>Protocol Handlers"]
        STATE_MGR["State Manager<br/>Value Cache<br/>Timestamps"]
        RESOURCE_MGR["Resource Manager<br/>Conflict Detection<br/>Allocation"]
    end
    
    subgraph HAL["Layer 1: Hardware Abstraction Layer"]
        PLUGIN_MGR["Plugin Manager<br/>Dynamic Loading<br/>Lifecycle"]
        
        subgraph GPIO_PLUGIN["GPIO Plugin"]
            GPIO_DRV["GPIO Driver<br/>Digital I/O<br/>PWM, Interrupt"]
            GPIO_CH["GPIO Channels"]
        end
        
        subgraph CAN_PLUGIN["CAN Plugin"]
            CAN_DRV["CAN Driver<br/>Message TX/RX<br/>Filtering"]
            CAN_BUS["CAN Bus Interface"]
        end
        
        subgraph ANALOG_PLUGIN["Analog Plugin"]
            ADC_DRV["ADC Driver<br/>Sampling<br/>Conversion"]
            DAC_DRV["DAC Driver<br/>Signal Gen<br/>Scaling"]
            ANALOG_CH["Analog Channels"]
        end
        
        subgraph CUSTOM_PLUGIN["Custom Plugin"]
            CUSTOM_DRV["User Plugin<br/>Custom Logic<br/>Extension"]
            CUSTOM_CH["Custom Channels"]
        end
    end
    
    HW["Physical Hardware<br/>ECU/DUT/Sensors"]
    
    Client1 -->|"HTTP<br/>REST Calls"| CH_EP
    Client1 -->|"HTTP"| TEST_EP
    Client1 -->|"HTTP"| FLASH_EP
    Client1 -->|"HTTP"| HEALTH_EP
    Client2 -->|"WebSocket<br/>Subscribe"| WS
    
    CH_EP -->|"Control"| CHANNEL_MGR
    TEST_EP -->|"Orchestrate"| EXECUTOR
    FLASH_EP -->|"Program"| PROG
    HEALTH_EP -->|"Query"| DISCOVERY
    
    EXECUTOR -->|"Read/Write"| CHANNEL_MGR
    EXECUTOR -->|"Log Data"| DATA_LOGGER
    EXECUTOR -->|"Validate"| VALIDATOR
    STATE_MACHINE -->|"Broadcast"| WS
    
    CHANNEL_MGR -->|"Query"| STATE_MGR
    CHANNEL_MGR -->|"Check"| RESOURCE_MGR
    BUS_MGR -->|"Route"| CHANNEL_MGR
    DISCOVERY -->|"Register"| CHANNEL_MGR
    
    STATE_MGR -->|"Update"| CHANNEL_MGR
    PLUGIN_MGR -->|"Create"| CHANNEL_MGR
    
    RESOURCE_MGR -->|"Allocate"| GPIO_DRV
    RESOURCE_MGR -->|"Allocate"| CAN_DRV
    RESOURCE_MGR -->|"Allocate"| ADC_DRV
    RESOURCE_MGR -->|"Allocate"| CUSTOM_DRV
    
    GPIO_DRV -->|"Control"| HW
    CAN_DRV -->|"Send/Recv"| HW
    ADC_DRV -->|"Read"| HW
    DAC_DRV -->|"Output"| HW
    CUSTOM_DRV -->|"Interface"| HW
    
    HW -->|"Sensor Data"| ADC_DRV
    HW -->|"Status"| GPIO_DRV
    HW -->|"Messages"| CAN_DRV
    
    DATA_LOGGER -->|"Write"| Artifacts["Output Artifacts<br/>CSV, JSON, Logs"]
    
    style API fill:#4A90E2,stroke:#333,stroke-width:2px,color:#fff
    style FlashManager fill:#50E3C2,stroke:#333,stroke-width:2px,color:#000
    style TestEngine fill:#F8E71C,stroke:#333,stroke-width:2px,color:#000
    style DevManager fill:#B8E986,stroke:#333,stroke-width:2px,color:#000
    style HAL fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style GPIO_PLUGIN fill:#FFB3BA,stroke:#333,stroke-width:1px
    style CAN_PLUGIN fill:#FFB3BA,stroke:#333,stroke-width:1px
    style ANALOG_PLUGIN fill:#FFB3BA,stroke:#333,stroke-width:1px
    style CUSTOM_PLUGIN fill:#FFB3BA,stroke:#333,stroke-width:1px
    style HW fill:#F5A623,stroke:#333,stroke-width:3px
```

**C4 Container Diagram - Detailed 5-Layer Architecture**: 
- **Layer 5 (REST API)**: Health, channels, tests, flashing endpoints; WebSocket; CORS/auth
- **Layer 4 (Flashing)**: Protocol handlers (UART/JTAG/SPI), verification, recovery
- **Layer 3 (Test Engine)**: Executor, state machine, logging, validation
- **Layer 2 (Device Manager)**: Discovery, channel/bus managers, state, resource allocation
- **Layer 1 (HAL)**: Plugin system with GPIO, CAN, Analog, Custom plugins; hardware drivers

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