# AI Agents in SDTB

The Software Defined Test Bench (SDTB) is built with an **Agent-Native** philosophy. By exposing low-level hardware capabilities through high-level semantic tools via the **Model Context Protocol (MCP)**, SDTB enables AI agents to monitor, control, and automate hardware testing with unprecedented ease.

## Why Agentic Testing?

Traditional hardware testing relies on static scripts that are difficult to maintain and adapt. Agentic testing allows for:
- **Dynamic Reasoning**: Agents can adapt their test strategy based on real-time hardware responses.
- **Natural Language Control**: Control complex test benches without writing a single line of Python or C.
- **Autonomous Troubleshooting**: Agents can identify, isolate, and often explain hardware faults by exploring signals semantically.

## Interaction Layers

### 1. Semantic Layer (MCP)
The primary interface for Large Language Models (LLMs). It provides tools like `read_channel` and `write_channel` with rich descriptions, allowing the model to understand *what* it is controlling, not just *how*.

### 2. Programmatic Layer (REST API)
Used by autonomous agents for high-speed data acquisition, logging, and integration into existing CI/CD pipelines.

## Common Agent Workflows

### Automated Bench Validation
*   **Prompt**: "Verify the bench is healthy."
*   **Agent Action**: 
    1.  Calls `connect_system`.
    2.  Calls `get_system_summary` to check device status.
    3.  Calls `list_channels` to verify mapping.
    4.  Performs sample reads on critical channels (e.g., `Power_Rail_12V`).

### Semantic Fault Injection
*   **Prompt**: "Test how the ECU handles a throttle sensor short to ground."
*   **Agent Action**:
    1.  Locates the `Throttle_Sensor` channel.
    2.  Writes `0.0` (simulating ground) to the channel.
    3.  Monitors the `ECU_Fault_Status` channel to verify the error code is triggered.

### Autonomous Calibration
*   **Prompt**: "Find the optimal PID values for the heater control."
*   **Agent Action**:
    1.  Iteratively writes new coefficients to `Heater_P`, `Heater_I`, and `Heater_D`.
    2.  Monitors `Temp_Sensor` for overshoot and settling time.
    3.  Analyzes trends and converges on optimal settings.

## Best Practices for Agent Developers

1.  **Lifecycle Management**: Ensure your agent always calls `connect_system` before operations and `disconnect_system` upon completion to prevent hardware resources from hanging.
2.  **Safety Limits**: SDTB enforces min/max ranges at the `Channel` level. Leverage these to ensure the agent cannot drive hardware into a destructive state.
3.  **Batching**: For complex validations involving many signals, use `read_channels` and `write_channels` to minimize round-trip latency.
4.  **Logging**: Use the system logs (available via SSE or `/system/logs`) to provide the agent with feedback on the physical impact of its actions.

## Example Claude Desktop Config
Connect Claude directly to your local bench:

```json
{
  "mcpServers": {
    "sdtb": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```
