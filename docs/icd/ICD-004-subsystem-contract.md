# ICD-004 — Subsystem Contract

## Purpose

Define the common runtime interface all subsystems follow.

## Common interface

Each subsystem shall support:

- `id()`

- `type()`

- `tick(context)`

- `receive(message)`

- `health()`

- `snapshot()`

## Health states

Each subsystem may be in one of:

- `Nominal`

- `Degraded`

- `Offline`

- `Failed`

- `Recovering`

## Mission computer behavior

### MC1

starts as active controller
emits heartbeat every configured interval
processes sensor data
emits status messages
may fail or go offline

## MC2

- starts in standby

- monitors MC1 heartbeat freshness

- if heartbeat timeout threshold exceeded, transitions active

- emits `FAILOVER_NOTICE`

- continues status generation as active controller

## Sensor behavior

A sensor shall:

- emit `SENSOR_DATA` every `rate_ticks`

- include `sensor_type`, `value`, `units`, `quality`, `valid`

- stop or degrade under applicable fault conditions

## Display behavior

A display shall:

- receive `STATUS`, `ALERT`, and `FAILOVER_NOTICE`

- maintain a local view of active controller and recent system state

- expose this through logs or snapshots

## Subsystem design rule

Subsystem logic shall not perform routing decisions. Subsystems create messages; bus handles delivery.
