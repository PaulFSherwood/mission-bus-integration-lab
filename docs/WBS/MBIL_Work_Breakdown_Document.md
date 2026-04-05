# MBIL Decomposition Working Document

## Purpose

This document breaks MBIL into the major areas that still need detailed design and implementation planning. It is not the ticket list itself. It is the layer **before** tickets.

The goal is that each area can later be turned into small GitHub issues without guessing what the work means.

Each section is decomposed in the same way:

- what must be defined
- what must be implemented
- what must be verified
- what questions or holes still need review

This lets the project move from:

high-level vision  
to  
clear engineering contracts  
to  
small implementable tickets

---

# 0. Foundation / Project Setup

This area is easy to forget, but it matters because it supports every later phase.

## What must be defined

Define:

- repository layout
- naming conventions
- branch naming rules
- issue naming rules
- pull request naming rules
- project status flow
- milestone names
- what counts as done for a ticket
- where documentation lives
- where tests live
- coding style expectations
- logging style expectations

## What must be implemented

Implement:

- repository initialization
- base folder structure
- CMake or build system skeleton
- test target skeleton
- docs folder structure
- config folder structure
- `.gitignore`
- README starter
- GitHub issue templates
- PR template
- GitHub Project fields and views
- milestone definitions

## What must be verified

Verify:

- repo clones cleanly
- project builds
- test framework runs
- folder layout matches docs
- one sample issue/PR can be created using the conventions

## Questions / holes to review

Review:

- do we want one repo or future submodules
- do we want all docs in markdown or some in LaTeX
- what is the minimum “done” definition for implementation tickets
- what testing framework will be used

---

# 1. Simulation Engine

This is the runtime controller of the whole system.

## What must be defined

Define the simulation engine in terms of:

### Responsibilities

- initialize the system
- own the main runtime loop
- advance time tick by tick
- stop when configured duration is reached
- coordinate subsystem updates
- invoke fault processing
- invoke bus processing
- invoke logging and snapshots
- enforce deterministic order

### Inputs

- system configuration
- scenario configuration
- registered subsystems
- bus reference
- fault engine reference
- logger / snapshot writer reference

### Outputs

- tick advancement
- ordered subsystem execution
- lifecycle events
- final run completion state
- logs and snapshots through helper components

### Internal state

- current tick
- max tick or duration
- running/stopped state
- subsystem registry
- execution order
- references to bus/fault/logger/config

### Timing and ordering rules

- fixed tick progression
- stable phase order every tick
- stable subsystem order every tick
- no hidden asynchronous behavior in MVP

### Failure behavior

- config load failure
- missing required component
- invalid runtime state
- subsystem throwing error or returning failure
- graceful stop vs hard fail policy

### Interfaces with other components

- calls fault engine at the correct phase
- calls subsystems in the correct phase
- calls bus processing after producers emit messages
- calls observability output at the end of tick

## What must be implemented

Implement at least:

- `SimulationEngine` class skeleton
- engine state model
- initialization flow
- shutdown flow
- current tick tracking
- max duration / stop condition
- subsystem registration
- deterministic subsystem ordering
- tick loop
- tick phases
- bus invocation hook
- fault engine invocation hook
- snapshot / logging invocation hook
- result / exit status reporting

## What must be verified

Verify:

- engine initializes cleanly
- engine advances the exact configured number of ticks
- engine stops at configured duration
- subsystem order is deterministic across runs
- fault engine is invoked in the correct phase
- bus is invoked in the correct phase
- logger/snapshot calls happen in the expected place
- identical scenario gives identical execution ordering

## Questions / holes to review

Review:

- should tick be integer only or include simulated time helper
- do we want pre-tick and post-tick hooks
- what happens if one subsystem is offline during registration
- does the engine own components or just reference them

---

# 2. Message Bus

This is the transport layer between subsystems.

## What must be defined

Define the bus in terms of:

### Responsibilities

- accept outgoing messages
- hold pending messages
- hold delayed messages
- apply routing rules
- support unicast
- support broadcast
- apply message-level fault effects
- deliver messages to recipients
- log lifecycle events

### Inputs

- messages emitted by subsystems
- current tick
- registered subsystem destinations
- active fault rules affecting messages

### Outputs

- delivered messages
- dropped messages
- delayed messages
- undeliverable message events
- trace/log records

### Data structures

- `Message`
- pending queue
- delayed queue
- registered subsystem map
- routing metadata
- broadcast identifier
- delivery result status

### Timing and ordering rules

- delivery only when `tick_due <= current_tick`
- deterministic ordering when multiple messages are ready
- clear rule for priority
- clear rule for tie-breaking
- broadcast behavior must be explicit

### Failure behavior

- destination missing
- destination offline
- message dropped
- message delayed
- message corrupted
- duplicate or invalid IDs
- full queue behavior if ever relevant

### Interfaces with other components

- receives messages from subsystems
- checks active faults with fault engine or fault matcher
- delivers to subsystem `receive()`
- logs through observability layer

## What must be implemented

Implement at least:

- `Message` data structure
- message type enum
- message metadata fields
- queue container for pending messages
- queue or holding structure for delayed messages
- subsystem registration with bus
- enqueue operation
- process operation
- delivery operation
- deterministic sort/order rules
- unicast routing
- broadcast routing
- undeliverable handling
- trace hooks for lifecycle events

## What must be verified

Verify:

- message can be created and queued
- ready message is delivered on correct tick
- delayed message waits until due tick
- dropped message is not delivered
- broadcast reaches all valid targets
- sender exclusion rule works for broadcast if used
- delivery order is deterministic
- missing destination is logged properly

## Questions / holes to review

Review:

- should routing table be static or derived from registry only
- does the bus mutate messages or create delivery records
- how should corruption be represented
- should message priority be in MVP or later

---

# 3. Fault Engine

This controls defined failure behavior.

## What must be defined

Define the fault engine in terms of:

### Responsibilities

- load fault definitions from scenario config
- activate faults at the right tick
- deactivate faults when expired
- target subsystem-level or message-level behavior
- apply effects such as drop, delay, corruption, offline
- log activation and resolution

### Inputs

- scenario fault definitions
- current tick
- message metadata
- subsystem IDs and states

### Outputs

- active fault set
- modified message behavior
- modified subsystem behavior
- fault lifecycle events

### Data structures

- fault definition model
- active fault registry
- target matching rules
- severity metadata
- duration / window fields

### Timing and ordering rules

- activation phase in tick must be fixed
- deactivation rules must be fixed
- overlapping fault behavior must be defined
- multiple matching faults must have precedence rules

### Failure behavior

- invalid fault config
- unknown target
- overlapping contradictory faults
- impossible effect for target type
- expired or never-activated fault handling

### Interfaces with other components

- engine calls fault engine each tick
- bus checks message-related fault effects
- subsystems check subsystem-related fault effects
- logger records fault events

## What must be implemented

Implement at least:

- fault definition model
- fault loader from config
- active fault tracking
- activation logic
- deactivation logic
- target matching logic
- subsystem offline fault
- message drop fault
- message delay fault
- message corruption fault
- precedence / combination rules
- fault event logging

## What must be verified

Verify:

- fault activates on configured tick
- fault deactivates on configured end tick
- subsystem offline prevents normal behavior
- message drop prevents delivery
- message delay changes delivery timing
- corruption marks payload invalid or altered
- activation/deactivation is logged
- repeated runs produce same fault timeline

## Questions / holes to review

Review:

- should random faults exist in MVP or only scripted
- how should multiple faults on same target combine
- where should stale-data behavior live: bus, subsystem, or both

---

# 4. Configuration Layer

This defines the system topology and scenario from files.

## What must be defined

Define the configuration layer in terms of:

### Responsibilities

- load system config
- load scenario config
- validate required fields
- define subsystem IDs and types
- define timing values
- define fault scenarios
- define logging and snapshot settings

### Inputs

- config files
- schema expectations
- defaults if allowed

### Outputs

- validated system configuration object
- validated scenario configuration object
- errors for invalid config

### Data structures

- system config model
- scenario config model
- subsystem config model
- timing config model
- logging config model
- fault config model

### Timing and ordering rules

- config must be loaded before runtime initialization
- validation must complete before engine start
- defaults vs required values must be explicit

### Failure behavior

- missing required field
- duplicate subsystem ID
- invalid type
- invalid interval or tick value
- invalid fault target
- malformed file

### Interfaces with other components

- simulation engine consumes validated config
- subsystem factory uses subsystem definitions
- fault engine uses scenario fault definitions
- logger uses logging config

## What must be implemented

Implement at least:

- config file parser
- config models
- validation routines
- duplicate ID checks
- interval/value checks
- system config loader
- scenario config loader
- error reporting
- defaults handling if desired
- object handoff into engine/factory

## What must be verified

Verify:

- valid config loads successfully
- duplicate subsystem IDs are rejected
- invalid types are rejected
- negative or zero invalid intervals are rejected
- missing required sections are rejected
- fault targets reference real components
- snapshot/logging settings are correctly passed forward

## Questions / holes to review

Review:

- do we want one config file or separate system/scenario files
- do we want strict schema validation now or later
- how much defaulting is acceptable

---

# 5. Mission Computers

These are the main control nodes.

## What must be defined

Define mission computers in terms of:

### Responsibilities

- receive sensor messages
- interpret data
- emit heartbeat messages
- emit status messages
- optionally emit commands
- maintain controller role
- participate in failover logic

### Inputs

- sensor data messages
- heartbeat messages if cross-monitoring
- config for intervals and thresholds
- fault state
- current role state

### Outputs

- heartbeat messages
- status messages
- command messages
- failover notice
- local health/state changes

### Internal state

- controller role: primary / backup / active / standby
- health state
- last heartbeat seen from peer
- missed heartbeat count
- latest sensor data cache
- active/inactive flag

### Timing and ordering rules

- heartbeat every configured interval
- failover only after threshold exceeded
- role changes must be deterministic
- takeover behavior must occur in defined phase

### Failure behavior

- primary offline
- backup offline
- stale sensor data
- corrupted input data
- split-brain prevention in MVP
- one-way failover policy in MVP

### Interfaces with other components

- receives via bus
- emits via bus
- health/fault effects may come from fault engine
- logs role changes through observability layer

## What must be implemented

Implement at least:

- mission computer class
- role state model
- heartbeat generation
- heartbeat reception / monitoring
- sensor message handling
- local latest-data cache
- status message generation
- failover threshold tracking
- backup takeover logic
- failover notice emission
- degraded / offline behavior hooks

## What must be verified

Verify:

- primary emits heartbeat on interval
- backup tracks heartbeat freshness
- backup does not take over too early
- backup takes over after configured timeout
- failover notice is emitted
- post-failover status uses new active controller
- offline primary stops normal behavior
- corrupted or invalid data is handled predictably

## Questions / holes to review

Review:

- does backup receive all data or only peer heartbeat
- should primary and backup both process sensor data in MVP
- what is the exact one-way failover rule

---

# 6. Sensors

These are the data producers.

## What must be defined

Define sensors in terms of:

### Responsibilities

- emit periodic sensor data
- identify sensor type
- include value, units, quality, validity
- respond to degraded or failed condition

### Inputs

- current tick
- sensor rate config
- sensor identity/type config
- fault state

### Outputs

- sensor data messages

### Internal state

- next emission tick or interval tracking
- current value model
- current quality/validity state
- health state

### Timing and ordering rules

- emit every configured number of ticks
- must not emit early
- if delayed or degraded, behavior must be explicit

### Failure behavior

- sensor offline
- invalid value
- reduced update rate
- corrupted data
- stale data if not updated

### Interfaces with other components

- emits through bus only
- may be affected by fault engine
- logs through observability layer

## What must be implemented

Implement at least:

- base sensor class or generic sensor
- sensor type metadata
- interval tracking
- message creation for sensor data
- validity/quality fields
- nominal emission behavior
- degraded emission behavior hook
- offline behavior hook

## What must be verified

Verify:

- sensor emits on correct interval
- message contains expected type and metadata
- quality and validity fields are included
- offline sensor stops emitting
- degraded behavior changes output as expected
- repeated run produces same nominal schedule

## Questions / holes to review

Review:

- do we need different concrete sensor subclasses in MVP
- how realistic do values need to be
- where should stale-data determination happen

---

# 7. Display Endpoint

This is the status-consuming endpoint.

## What must be defined

Define the display endpoint in terms of:

### Responsibilities

- receive status messages
- receive failover messages
- maintain current active controller view
- reflect degraded or faulted conditions
- expose human-readable state through logs or snapshots

### Inputs

- status messages
- alerts
- failover notices
- possibly sensor summaries if desired

### Outputs

- local state update
- display/state logs
- snapshot-visible summary

### Internal state

- current active controller
- last received status
- recent alerts
- degraded/fault flags

### Timing and ordering rules

- updates when messages arrive
- snapshot content must reflect last known state at snapshot time

### Failure behavior

- missing status updates
- stale display state
- corrupted status message
- display offline fault

### Interfaces with other components

- receives via bus
- contributes readable state to observability layer
- fault engine may mark it offline

## What must be implemented

Implement at least:

- display class
- receive handler
- internal state cache
- active-controller tracking
- alert/failover tracking
- summary output for log/snapshot

## What must be verified

Verify:

- display updates active controller on status/failover message
- display records degraded conditions
- offline display stops updating
- stale or missing input can be recognized if required
- snapshot includes display state

## Questions / holes to review

Review:

- should display only log, or also own a summary object
- does display need command messages in MVP or only status and failover

---

# 8. Observability Layer

This is one of the most important portfolio pieces.

## What must be defined

Define observability in terms of:

### Responsibilities

- structured logging
- event tracing
- subsystem state visibility
- message lifecycle visibility
- snapshot capture
- auditable failover and fault events

### Inputs

- events from engine
- events from bus
- events from fault engine
- events from subsystems
- current state snapshot data

### Outputs

- log records
- event records
- periodic snapshots

### Data structures

- log/event record format
- snapshot record format
- categories and severity
- trace correlation identifiers

### Timing and ordering rules

- critical events must always be logged
- snapshot interval must be configurable
- logs should preserve event order within run

### Failure behavior

- logger unavailable
- malformed event input
- snapshot failure
- fallback behavior if output fails

### Interfaces with other components

- all major components emit events to logger
- engine triggers snapshots
- bus provides lifecycle hooks
- fault engine provides activation hooks

## What must be implemented

Implement at least:

- logger class
- event record structure
- message lifecycle logging hooks
- subsystem state logging hooks
- fault activation/deactivation logging
- failover logging
- snapshot writer
- configurable snapshot interval
- log formatting in structured form

## What must be verified

Verify:

- critical events appear in logs
- message lifecycle events are traceable
- fault activation and resolution are logged
- failover is fully visible
- snapshots occur at configured interval
- snapshot reflects active controller and subsystem states
- repeated run produces same event ordering

## Questions / holes to review

Review:

- JSON logs or key-value text first
- one combined logger or separate snapshot writer
- how much trace correlation is needed in MVP

---

# 9. High-Level Interaction Model

This is the system behavior story across components.

## What must be defined

Define the interaction model in terms of:

### Responsibilities

This area exists to define who talks to whom and in what pattern.

### Required interactions

- sensors generate data
- mission computers receive sensor data
- mission computers generate heartbeats and status/commands
- bus routes all messages
- display receives status and failover notices
- fault engine may modify or interrupt behavior
- observability layer records key events

### Timing and ordering rules

- interactions occur in fixed phases
- no direct subsystem-to-subsystem calls in MVP
- all communication goes through bus

### Failure behavior

- message blocked by fault
- sender offline
- receiver offline
- stale data paths
- failover path

### Interfaces with other components

- this section informs ICDs and integration tests more than code directly

## What must be implemented

This area mostly drives design and tests, but implementation implications include:

- enforcing bus-mediated communication
- rejecting hidden direct coupling
- making role-change paths explicit
- making cross-component event flow observable

## What must be verified

Verify:

- subsystems communicate through bus only
- expected message paths occur in normal operation
- altered paths occur under fault
- failover path occurs as documented

## Questions / holes to review

Review:

- do any components currently cheat and talk directly
- do we need a formal message path diagram in docs

---

# 10. Primary Runtime Flow

This is the exact order of work each tick.

## What must be defined

Define runtime flow in terms of:

### Tick phases

1. advance current tick
2. activate/deactivate faults
3. let sensors emit if due
4. let mission computers update and emit heartbeat/status
5. process bus and deliver ready messages
6. allow recipients to consume delivered messages
7. write logs and snapshots

### Responsibilities

- make this order fixed
- make it documented
- make code follow it exactly

### Failure behavior

- what happens if one phase fails
- whether runtime halts or degrades
- whether logging still occurs on failure

### Interfaces with other components

- directly drives engine orchestration
- informs unit/integration tests

## What must be implemented

Implement at least:

- a concrete phase order in engine code
- phase boundaries that are visible in logs if useful
- clear call points for faults, subsystems, bus, and snapshots

## What must be verified

Verify:

- phases occur in documented order
- no component is called out of phase
- failover timing matches phase order
- identical run preserves phase sequence

## Questions / holes to review

Review:

- does delivery happen in same tick as generation or next phase only
- when exactly do recipients consume delivered messages
- do snapshots happen before or after delivery effects settle

---

# 11. Testing / Verification

This is needed from the beginning, not just at the end.

## What must be defined

Define testing in terms of:

### Test levels

- unit tests
- component tests
- scenario / integration tests

### Unit test targets

- message model
- bus routing
- delay/drop/corruption handling
- engine tick count
- deterministic ordering
- heartbeat timeout logic
- failover trigger logic
- config validation
- snapshot scheduling

### Scenario tests

- normal operation
- primary failure and backup takeover
- delayed message scenario
- dropped message scenario
- corrupted message scenario
- offline subsystem scenario

### Success rules

- expected tick/order behavior
- expected log events
- expected active controller
- expected message delivery or non-delivery

## What must be implemented

Implement at least:

- test framework setup
- test build target
- first smoke test
- unit tests by component as they become stable
- scenario test harness or scripted verification path

## What must be verified

Verify:

- tests run from clean checkout
- tests are linked to major behavior
- critical failover and fault paths are covered
- deterministic behavior is checked directly, not assumed

## Questions / holes to review

Review:

- what framework will be used
- do scenario tests inspect logs, state objects, or both
- what is minimum coverage for MVP credibility

---

# 12. Documentation / ICD Completion

This is another area that still needs controlled decomposition.

## What must be defined

Define documentation work in terms of:

### Required docs

- project charter
- system context
- system overview ICD
- message contract ICD
- bus contract ICD
- subsystem contract ICD
- fault/observability contract ICD
- architecture overview
- test plan
- fault scenario descriptions
- README

### Responsibilities

- each doc must define boundaries, not repeat vague goals
- docs must be updated when implementation changes core behavior

## What must be implemented

Implement at least:

- baseline versions of all docs
- document numbering/naming convention
- cross-references between docs
- update process for changed contracts

## What must be verified

Verify:

- docs match code
- docs match config expectations
- docs define acceptance boundaries clearly enough to derive tickets
- reviewer can understand system from docs alone

## Questions / holes to review

Review:

- what is doc baseline before coding begins
- which docs can stay lightweight for MVP
- how often docs should be updated

---

# 13. Recommended Decomposition Order

To avoid chaos, decompose the project into ticket-ready detail in this order:

1. Foundation / Project Setup
2. Simulation Engine
3. Message Bus
4. Configuration Layer
5. Fault Engine
6. Mission Computers
7. Sensors
8. Display Endpoint
9. Observability Layer
10. Primary Runtime Flow
11. Testing / Verification
12. Documentation / ICD Completion
13. High-Level Interaction Model review pass

That order builds the skeleton first, then transport, then behavior, then proof.

---

# 14. How to Use This Document

Use this document as a staging area.

When you are ready to work a new area:

1. pick one major section
2. turn its “what must be defined” items into design/ICD tickets if needed
3. turn its “what must be implemented” items into code tickets
4. turn its “what must be verified” items into test tickets
5. check its “questions / holes” before starting serious implementation

That way GitHub stays clean, and you only create the tickets you are actually ready to manage.

---

# 15. Simple Summary

This document exists so you do not have to ask “where do I start” every time you look at a big project section.

Instead, each section becomes:

- definition work
- implementation work
- verification work
- hole review
