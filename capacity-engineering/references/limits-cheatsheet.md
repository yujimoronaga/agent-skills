# Limits cheat sheet — provisional starting values

> **These numbers are starting points only, not evidence.** Providers change limits, defaults vary by account, region and plan, and new accounts often start lower. Verify each one in Stage 2: check the account's own value first, then the official docs, and record the source URL and date in `.capacity/limits.md`.

## Read-only commands for real account values (show the user first)
```bash
# AWS — any service's quotas (default vs applied)
aws service-quotas list-service-quotas --service-code lambda
aws service-quotas list-aws-default-service-quotas --service-code lambda
aws lambda get-account-settings                 # ConcurrentExecutions, UnreservedConcurrentExecutions
aws lambda get-function-concurrency --function-name <fn>
aws apigateway get-account                      # throttleSettings (REST)
aws dynamodb describe-limits
aws ses get-send-quota
# Postgres / MySQL
psql -c "SHOW max_connections;"
mysql -e "SHOW VARIABLES LIKE 'max_connections';"
# Azure
az functionapp show -g <rg> -n <app> --query "{plan:serverFarmId, scale:siteConfig.functionAppScaleLimit}"
# GCP
gcloud run services describe <svc> --region <r> --format="yaml(spec.template)"
```

## AWS
| Service | Limit | Typical default | Hard/adj | When exceeded |
|---|---|---|---|---|
| Lambda | Concurrent executions per region (shared by all functions in the account) | 1,000; new accounts can be much lower | adjustable | Throttle (sync: 429; async: retried, then dropped/DLQ) |
| Lambda | Scaling rate per function | +1,000 concurrency every 10s | hard | Throttles during a spike |
| Lambda | Timeout | max 900s | hard | Function killed |
| Lambda | Sync invoke payload | 6 MB request/response | hard | Invoke error |
| Lambda | Async invoke payload | 256 KB, raised to 1 MB in 2025 (verify) | hard | Invoke error |
| Lambda ← SQS trigger | Scale-up rate | ~+300 concurrent executions/min (provisioned mode faster) | mode | Backlog at spike start |
| Lambda ← SQS trigger | Maximum concurrency setting | 2–1,000 per trigger | config | Caps the worker's throughput at max ÷ duration |
| SQS ↔ Lambda | Visibility timeout rule | ≥ 6× function timeout (AWS guidance) | config | Messages redelivered while still processing → duplicates |
| Lambda | Requests/s per function | 10× its concurrency | hard | Throttle |
| API Gateway HTTP API | Integration timeout | 30s | hard | 503/504 |
| DynamoDB on-demand | Ramp | New tables start lower and grow toward 2× the previous peak | — | Throttling during a first big spike |
| API Gateway REST | Account throttle per region | 10,000 RPS steady, 5,000 burst | adjustable | 429 |
| API Gateway REST | Integration timeout | 29s default (can be raised for regional/private APIs, verify) | partly | 504 |
| API Gateway REST | Payload | 10 MB | hard | 413 |
| API Gateway HTTP API | Integration timeout | 30s | hard | 503/504 |
| ALB → Lambda | Request/response body | 1 MB | hard | 502 |
| SQS standard | Throughput | Nearly unlimited | — | — |
| SQS standard | In-flight messages | 120,000 | adjustable | OverLimit error |
| SQS FIFO | Throughput | 300 msg/s per action (3,000 with batching); high-throughput mode much higher | mode | Throttle |
| SQS | Message size | 256 KB, raised to 1 MiB in 2025 (verify) | hard | Send error |
| DynamoDB | Per partition | 3,000 RCU / 1,000 WCU | hard | ProvisionedThroughputExceeded (hot key) |
| DynamoDB | On-demand per-table max | 40,000 RRU / 40,000 WRU | adjustable | Throttle |
| DynamoDB | Item size | 400 KB | hard | ValidationException |
| RDS Postgres | max_connections | Depends on instance memory (small instances ≈ 80–200) | parameter | "too many connections" |
| Kinesis | Per shard write | 1 MB/s or 1,000 records/s | hard (add shards) | ProvisionedThroughputExceeded |
| Kinesis | Per shard read | 2 MB/s, 5 GetRecords/s | hard | Throttle |
| SES | Sandbox | 1 msg/s, 200/day | request production | Throttling |

## Azure
| Service | Limit | Typical default | Notes |
|---|---|---|---|
| Functions Consumption | Max scale-out instances | 200 Windows / 100 Linux | Hard per app on this plan. Flex Consumption / Premium go higher |
| Functions Consumption | Timeout | 5 min default, 10 min max | |
| Functions (HTTP) | Request timeout | 230s at the front-end load balancer | Use the async pattern for longer work |
| Azure SQL | Max workers/sessions | Per tier/DTU/vCore | Check the tier docs |

## GCP
| Service | Limit | Typical default | Notes |
|---|---|---|---|
| Cloud Run | Max instances per service | 100 default (configurable; regional quota also applies) | |
| Cloud Run | Concurrency per instance | 80 default, max 1000 | Instances needed ≈ concurrency ÷ per-instance concurrency |
| Cloud Run | Request timeout | 5 min default, 60 min max | |
| Cloud SQL | max_connections | Depends on tier memory | |

## Self-hosted / runtime defaults
| Thing | Default | Notes |
|---|---|---|
| PostgreSQL max_connections | 100 | Each connection is a process (memory) |
| MySQL max_connections | 151 | |
| Redis maxclients | 10,000 | Single-threaded command execution |
| Linux open files (ulimit -n) | often 1,024 | Sockets count |
| Nginx worker_connections | 512 compiled default (1,024 in common configs) | × worker_processes |
| App DB pool (per instance) | HikariCP 10, SQLAlchemy 5+10 overflow, Prisma ≈ num_cpus×2+1 | × number of instances |

## Third-party APIs (always check the account's own tier)
| Provider | What limits | Where to look |
|---|---|---|
| Stripe | Requests/s per account (live vs test mode differ) | Stripe docs "Rate limits" |
| OpenAI / Anthropic / other LLMs | RPM, input/output tokens per minute, by usage tier | Provider console → limits |
| GitHub API | 5,000 req/h per authenticated user/token (REST); secondary limits | `GET /rate_limit` |
| SendGrid / Mailgun / SES | Sends per second/day by plan | Account dashboard |
| Google Maps / other per-key APIs | QPS + daily quota per key | Cloud console quotas |
