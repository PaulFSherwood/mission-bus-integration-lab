# MBIL working design, v0.1

## ICD-001 — System Overview

## Purpose

> Define the major runtime parts of MBIL and their responsibilities.

### System components

**MBIL contains:**

- Simulation Engine

- Bus

- Fault Engine

- Logger / Snapshot Writer

- Subsystems

**Subsystems in MVP**

- `MC1` primary mission computer

- `MC2` backup mission computer

- `ALT1` altitude sensor

- `TMP1` temperature sensor

- `DSP1` display endpoint

## High-level flow

**Each tick:**

1. simulation engine advances tick

2. fault engine activates/deactivates scheduled faults

3. sensors generate messages if due

4. mission computers process state and emit heartbeats or status

5. bus routes ready messages

6. endpoints receive delivered messages

7. logger records events

8. optional snapshot is written

### Design rule

All interactions between subsystems occur through the bus. No subsystem directly calls another subsystem’s behavior logic.
