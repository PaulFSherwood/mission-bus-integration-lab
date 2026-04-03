# ICD-005 — Fault and Observability Contract

## Purpose

Define how MBIL models faults and how events are observed.

## Fault categories

The MVP fault engine shall support:

- `subsystem_offline`

- `message_drop`

- `message_delay`

- `message_corruption`

## Fault definition fields

Each fault shall define:

- `fault_id`

- `fault_type`

- `target`

- `start_tick`

- `end_tick or duration`

- `effect`

- `severity`

## Example targets

- subsystem ID

- source ID

- destination ID

- message type

## Fault activation behavior

When a fault becomes active, the system shall log:

- fault ID

- activation tick

- target

- intended effect

When a fault ends, the system shall log deactivation.

## Observability requirements

The system shall generate structured logs with at least:

- `tick`

- `category`

- `event`

- `subsystem_id`

- `message_id` when applicable

- `trace_id` when applicable

- `details`

## Snapshot requirements

At configurable intervals, MBIL shall emit a state snapshot containing:

- current tick

- active controller

- subsystem health states

- active faults

- pending bus queue count

- latest known sensor values

## Mandatory auditable events

These events must always be visible:

- fault activation

- fault deactivation

- heartbeat timeout

- failover trigger

- controller role change

- dropped or delayed message

- subsystem offline transition
