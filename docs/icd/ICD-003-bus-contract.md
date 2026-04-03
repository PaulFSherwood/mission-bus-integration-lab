# ICD-003 — Bus Contract

## Purpose

Define bus responsibilities and delivery behavior.

## Bus responsibilities

The bus shall:

- accept outbound messages from subsystems

- store pending messages

- apply fault effects to matching messages

- deliver ready messages to destination subsystems

- support broadcast delivery

- log message lifecycle events

## Bus operations

The bus exposes at least these conceptual operations:

- `enqueue(message)`

- `process(current_tick)`

- `deliver(message, subsystem)`

- `register_subsystem(id, ref)`

## Delivery rules

A message is deliverable when:

- `tick_due <= current_tick`

- source subsystem is not blocked from sending

- message was not dropped by a fault rule

- destination exists, or message is broadcast

## Broadcast rule

If `destination_id == ALL`, bus shall deliver to all registered subsystems except the sender unless explicitly configured otherwise.

## Fault interaction

The bus is where these message-level faults apply:

- drop

- delay

- corrupt

- timeout/stale consequence

## Bus logging

The bus shall log these events:

- created

- enqueued

- delayed

- dropped

- delivered

- undeliverable
