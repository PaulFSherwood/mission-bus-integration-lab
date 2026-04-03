# ICD-002 — Message Contract

## Purpose

> Define the common transport object used across the system.

## Message fields

**Every message shall contain:**

- `message_id` : unique identifier

- `sequence_number` : monotonically increasing per run

- `tick_created` : tick when generated

- `tick_due` : tick eligible for delivery

- `source_id` : sender subsystem ID

- `destination_id` : target subsystem ID or broadcast ID

- `message_type` : enum

- `priority` : integer or enum

- `trace_id` : correlation identifier

- `payload` : structured data object

- `valid` : boolean, defaults true
  

## MVP message types

- `HEARTBEAT`

- `SENSOR_DATA`

- `STATUS`

- `COMMAND`

- `FAILOVER_NOTICE`

- `ALERT`

## Payload rules

Payload shall be structured, not raw strings.

Examples:

## HEARTBEAT payload

- controller_role

- health_state

## SENSOR_DATA payload

- sensor_type

- value

- units

- quality

- valid

## STATUS payload

- active_controller

- system_mode

- health_summary

## COMMAND payload

- command_name

- parameter

## Message ordering

When multiple messages are eligible for delivery on the same tick, order shall be:

1. higher priority first

2. lower `tick_created`

3. lower `source_id` lexical order

4. lower `sequence_number`

This gives deterministic replay.
