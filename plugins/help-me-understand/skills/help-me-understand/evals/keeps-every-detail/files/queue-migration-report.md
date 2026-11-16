# Moving the job queue from Postgres polling to Redis streams

Workers poll the `jobs` table every 2 seconds. At 40 workers that is 1,200 polls a minute, and 97% of them find nothing. Moving to Redis streams removes the polling and cuts median job latency from 1,100 ms to 35 ms in a staging test of 50,000 jobs.

## What each job type gains

Measured on staging over 50,000 jobs, largest gain first.

| Job type | Jobs per day | Latency now | Latency on streams | Retries now | Retries on streams |
|---|---|---|---|---|---|
| send_email | 18,400 | 1,150 ms | 31 ms | 2.1% | 0.4% |
| resize_image | 9,200 | 1,480 ms | 44 ms | 3.8% | 1.9% |
| sync_crm | 6,100 | 1,090 ms | 38 ms | 6.5% | 6.2% |
| build_invoice_pdf | 4,750 | 2,300 ms | 120 ms | 1.2% | 1.1% |
| reindex_search | 3,900 | 1,020 ms | 29 ms | 0.3% | 0.3% |
| expire_sessions | 2,880 | 990 ms | 27 ms | 0.0% | 0.0% |
| export_csv | 1,310 | 4,800 ms | 3,900 ms | 4.4% | 4.0% |
| charge_card | 870 | 1,060 ms | 33 ms | 0.9% | 0.9% |
| send_webhook | 640 | 1,130 ms | 36 ms | 11.2% | 10.8% |

`export_csv` barely improves because its time goes into the export itself, not into waiting to be picked up.

## Why it works

- Workers block on `XREADGROUP` and wake when a job arrives, so there is no polling interval to wait out.
- Each consumer group tracks its own pending entries, so a crashed worker's jobs are reclaimed with `XAUTOCLAIM` after 60 seconds.
- Postgres stops serving 1,200 `SELECT ... FOR UPDATE SKIP LOCKED` queries a minute, which were 14% of its CPU.

## Tried and rejected

- Lowering the poll interval to 200 ms: latency fell to 140 ms but Postgres CPU rose from 14% to 61%.
- `LISTEN/NOTIFY`: notifications are lost while a worker reconnects, and PgBouncer in transaction mode does not support it.
- RabbitMQ: it works, but it adds a third system to run, and the team already operates Redis.
- Redis lists with `BRPOPLPUSH`: no consumer groups, so reclaiming a crashed worker's job needs custom code.
- SQS: 20 ms cheaper per job than polling, but FIFO queues cap at 300 messages a second without batching.

## Worker configuration

```yaml
queue:
  backend: redis_streams
  url: ${REDIS_URL}
  stream: jobs:{{ env }}
  group: workers
  consumer: ${HOSTNAME}
  block_ms: 5000
  batch_size: 10
  claim_idle_ms: 60000
  max_deliveries: 5
  dead_letter_stream: jobs:{{ env }}:dead
  trim:
    strategy: maxlen
    approximate: true
    length: 200000
charge_card:
  backend: postgres   # stays on Postgres until idempotency keys ship
```

## Check before the switch

- Confirm that `charge_card` stays on Postgres: a redelivered charge without an idempotency key bills the customer twice.
- Set Redis `maxmemory-policy` to `noeviction`; with `allkeys-lru`, Redis would evict pending jobs under memory pressure.
- Run both backends for 7 days with `send_email` only, then move the other job types.
- The staging test used one Redis node. Production runs a 3-node Sentinel setup, and failover behaviour was not tested.
