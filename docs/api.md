# SDTB API Reference

The Software Defined Test Bench (SDTB) exposes a REST API built with FastAPI. All endpoints are relative to the server root (default: `http://localhost:8000`).

## System Management

### GET `/system`

Returns overall system health, status, and version information.

### GET `/system/config`

Retrieves current system configuration (system.json).

### PUT `/system/config`

Updates the system configuration.
- **Body**: `SystemConfig` object.

### POST `/system/connect`

Initiates the system connection sequence (discovery and hardware mapping for all enabled devices).

### POST `/system/disconnect`

Gracefully disconnects all hardware and stops background loops.

### POST `/system/restart`

Performs a full system restart (auto-disconnect, re-initialize, and re-discover).

### POST `/system/fault/clear`

Global safety mechanism to clear all faults on all devices.

### GET `/system/logs/stream`

SSE endpoint for real-time system logs.

### GET `/system/stream`

Unified Server-Sent Events (SSE) stream multiplexing logs, channels, and device signals over a single connection.

### GET `/system/config/channels`

Retrieves channel-to-signal mapping configuration.

### PUT `/system/config/channels`

Configures channel-to-device-signal mappings.
- **Body**: List of `ChannelConfig` objects.

---

## Device Management

### GET `/device`

Lists all discovered hardware devices with their current connection and enabled status.

### GET `/device/{device_id}`

Retrieves detailed information (vendor, model, firmware) about a specific device.

### POST `/device/{device_id}/toggle`

Enable or disable a specific device. Disabling a device prevents it from connecting during `system/connect`.
- **Body**: `{"enabled": boolean}`

### POST `/device/{device_id}/restart`

Re-initialize and restart a specific hardware device.

### GET `/device/{device_id}/signal`

Lists all raw hardware signals exposed by the device.

### GET `/device/{device_id}/signal/{signal_id}/info`

Retrieves detailed metadata (min, max, unit, resolution) for a specific hardware signal.

### GET `/device/{device_id}/signal/{signal_id}`

Read the current raw hardware signal value.

### PUT `/device/{device_id}/signal/{signal_id}`

Write a raw value directly to a hardware signal.
- **Body**: `{"value": float}`

### GET `/device/{device_id}/signal/{signal_id}/stream`

SSE stream for real-time raw signal updates from the hardware.

### GET `/device/{device_id}/signal/{signal_id}/fault`

List available fault injection types (Short to Ground, Open, etc.) supported by this specific signal.

### POST `/device/{device_id}/signal/{signal_id}/fault`

Inject a hardware fault into the signal.
- **Body**: `{"fault_id": string}`

### DELETE `/device/{device_id}/signal/{signal_id}/fault`

Clear the active hardware fault on the signal and restore normal operation.

---

## Channel Operations

Logical channels map to raw device signals with scaling, calibration, and unit conversion.

### GET `/channel`

Lists all configured logical channels.

### GET `/channel/{channel_id}`

Reads the scaled/calibrated value of a channel.

### PUT `/channel/{channel_id}`

Writes a scaled value to a channel.
- **Body**: `{"value": float}`
- **Constraint**: Returns `409 Conflict` if a test sequence is currently running.

### GET `/channel/{channel_id}/info`

Get detailed channel metadata, mapping info, and conversion strategy.

### GET `/channel/{channel_id}/status`

Get current operational status of the channel (based on its parent device).

### GET `/channel/{channel_id}/stream`

SSE endpoint for real-time updates of a channel's scaled value.

---

## Test Execution

### POST `/test/run`

Executes a test sequence provided in JSONL format.
- **Body**: `text/plain` (JSONL content)
- **Response**: Returns confirmation that the test has started in the background.

### POST `/test/stop`

Aborts the currently running test sequence and clears the execution queue.

### GET `/test/status`

Returns the current status of the test engine (is_running, abort_requested).

### GET `/test/history`

Retrieves the history of all executed test steps in the current session.

---

## Flashing Protocols

### GET `/flash/protocols`

Lists all discovered flash protocols and their static configurations.

### POST `/flash/connect`

Connects to a specific flash target (ECU).
- **Query Param**: `flash_id: string`

### POST `/flash/disconnect`

Disconnects from a specific flash target.
- **Query Param**: `flash_id: string`

### POST `/flash`

Starts a flashing operation using multipart/form-data.
- **Constraint**: Maximum file size is **10MB**.
- **Form Data**:
  - `flash_id`: ID of the protocol to use.
  - `file`: The binary file to flash.
  - `params`: (Optional) JSON string of parameters.

### GET `/flash/status`

Gets the status and progress (0-100%) of a specific flash operation.
- **Query Params**: `flash_id`, `execution_id`

### GET `/flash/log`

SSE endpoint to stream live logs for an active flash operation.
- **Query Params**: `flash_id`, `execution_id`

### POST `/flash/abort`

Aborts an ongoing flashing operation.
- **Query Params**: `flash_id`, `execution_id`

### GET `/flash/history`

Retrieve the history of flashing operations.

---

## UI Configuration

### GET `/ui/config`

Retrieves the current UI layout and widget configuration (ui.json).

### PUT `/ui/config`

Updates the UI layout and widget configuration.
- **Body**: `UIConfig` object.

---

## MCP Integration

### GET `/mcp/sse`

Entry point for Model Context Protocol (MCP) clients using SSE transport. Provides the endpoint for the EventSource connection.

### POST `/mcp/messages`

Standard MCP endpoint for receiving client messages (requests/notifications) once the SSE connection is established.
