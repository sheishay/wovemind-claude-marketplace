---
type: llm
focus: trace
weight: 1
---

All five rejected options appear with their reasons and numbers: the 200 ms poll interval (140 ms latency, CPU from 14% to 61%), LISTEN/NOTIFY (lost notifications, PgBouncer transaction mode), RabbitMQ (a third system to run), Redis lists with BRPOPLPUSH (no consumer groups), and SQS (300 messages a second on FIFO queues)
