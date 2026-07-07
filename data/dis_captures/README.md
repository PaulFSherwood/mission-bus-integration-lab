# DIS Captures

Runtime-only DIS/replay capture files are written here.

Two capture types can appear here:

1. Raw DIS UDP packet capture
   - Produced when source is `dis` and raw DIS recording is enabled.
   - Stores UDP datagrams as base64 inside JSONL records.

2. MBIL translated DIS JSON replay
   - Produced when `Record selected source as DIS replay` is enabled.
   - Lets X-Plane or Synthetic be replayed later through the existing DIS replay source.
   - This is not real binary DIS Entity State PDU output yet; it is MBIL JSON telemetry stored in the same replay wrapper.

Do not commit `*.jsonl` files from this directory.
