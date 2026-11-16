---
type: llm
focus: trace
weight: 1
---

All four pre-switch checks appear (charge_card stays on Postgres because of double billing, maxmemory-policy noeviction, 7 days with send_email only, untested 3-node Sentinel failover) and all three reasons it works (XREADGROUP blocking, XAUTOCLAIM after 60 seconds, 1,200 SKIP LOCKED queries a minute at 14% of CPU)
