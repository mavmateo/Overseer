# Site WAN Outage Runbook

## Objective

Maintain lossless ingest for up to 72 hours while a site is disconnected from the core platform.

## Procedure

1. Confirm Mosquitto is healthy and accepting local telemetry.
2. Check the site forwarder spool depth and free disk headroom.
3. Verify command pathways are in degraded mode and that no high-impact actions are pending.
4. Keep local dashboards active from buffered data if available.
5. After WAN recovery, monitor forwarder replay rate, Kafka lag, and dedupe counters until backlog reaches zero.

## Escalation

- Escalate when spool usage exceeds 80% of provisioned disk.
- Escalate when command acknowledgement traffic is delayed beyond the configured timeout.
- Escalate if replay stalls for more than 15 minutes after connectivity returns.

