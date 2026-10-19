# Capacity model — method, model.json format, mandatory checks, mitigations

## Core arithmetic
- **Demand at a component** = incoming req/s × `fanout`, where fanout is the number of calls this component receives per incoming request. A request that runs 3 DB queries has DB fanout 3.
- **Concurrency (Little's law)** = arrival rate × time in system. For example, 500 req/s × 0.4s = 200 concurrent executions.
- **Connections held**: if each instance of component A holds `k` connections to B, then connections to B = concurrency(A) × k. This holds even when A is idle, because of warm instances and pool sizes. This is the classic Lambda → RDS failure.
- **Utilization** = (demand + baseline used by others) / limit.
- **Break point** = the incoming req/s at which utilization reaches 100% = (limit − baseline) / (demand per incoming req/s).
- **Status**: OK under 70%, RISK between 70% and 100%, FAIL at 100% or more. Keep 30% headroom for variance and retries.
- **Retries amplify load.** At error rate e with r retries, effective demand ≈ demand × (1 + e + e² + … + eʳ). Near saturation e rises, so the curve goes vertical.
- **Burst is a separate limit.** Scaling speed (e.g. new instances per minute), token-bucket burst size, and cold starts can fail a spike that steady state would handle.
- **Timeouts must shrink going downstream.** The client timeout must exceed the gateway timeout, which must exceed compute, which must exceed DB/HTTP calls. Otherwise work continues after the caller has given up, which doubles load during incidents.
- **Hot keys**: per-partition and per-key limits (DynamoDB partitions, Kinesis shards, Redis single thread) break at a fraction of the total limit when traffic is skewed.

## model.json format
`examples/serverless-api.json` is the full reference: CloudFront → API Gateway → Lambda → RDS + Kinesis → consumer Lambda. Its shape:

```json
{
  "title": "Order API", "description": "One sentence shown under the title.",
  "scenarios": { "expected": 50, "peak": 500, "spike": 2000 },
  "globals": {
    "lambda_account_concurrency": { "value": 1000, "label": "Lambda concurrency quota", "integer": true,
      "min": 10, "max": 100000, "adjustable": true, "verified": false, "source": "<url>", "checked": "2026-10-19" }
  },
  "components": [
    { "id": "stream", "name": "Kinesis order-events", "kind": "Stream",
      "fanout": "api_fn.fanout * records_per_request", "duration_s": 0.02, "timeout_s": 2,
      "connects_to": ["consumer"],
      "params": {
        "shards": { "value": 2, "label": "Shards", "integer": true, "min": 1, "max": 500 },
        "write_records_per_shard": { "value": 1000, "label": "Write limit per shard (records/s)" },
        "records_per_request": { "value": 2, "label": "Records per API request" }
      },
      "limits": [
        { "name": "write records/s", "type": "rps", "value": "shards * write_records_per_shard",
          "adjustable": true, "verified": false, "source": "", "checked": "", "failure": "ProvisionedThroughputExceeded" }
      ] },
    { "id": "consumer", "name": "Lambda consumer", "kind": "Compute", "async": true,
      "fanout": "stream.fanout / batch_size", "duration_s": 0.5,
      "params": { "parallelization_factor": { "value": 2, "integer": true, "min": 1, "max": 10 },
                  "batch_size": { "value": 100, "integer": true } },
      "limits": [
        { "name": "account concurrency (shared)", "type": "concurrency", "shared_id": "lambda_account",
          "value": "lambda_account_concurrency", "baseline": "other_lambda_usage",
          "demand": "stream.shards * parallelization_factor" },
        { "name": "processing rate", "type": "rps", "demand": "stream.rps",
          "value": "stream.shards * parallelization_factor * batch_size / duration_s" }
      ] }
  ],
  "fixes": [
    { "title": "Add shards (2 → 4)", "type": "config", "effort": "S", "cost": "per shard-hour",
      "detail": "…", "set": { "stream.shards": 4 } },
    { "title": "Raise Lambda concurrency quota", "type": "quota", "set": { "lambda_account_concurrency": 3000 },
      "quota": { "service": "AWS Lambda", "name": "Concurrent executions", "current": 1000, "requested": 3000, "justification": "…" } }
  ],
  "notes": ["Assumptions and open risks, one per line"]
}
```

**Every resource variable is editable.** Anything the user might want to change goes in `globals` (account-wide quotas and shared values) or in a component's `params`: shards, parallelization factor, batch size, reserved concurrency, max_connections, pool size, instance count, cache hit ratio, API quota, and so on. Each one gets a `label`, and optionally `min`, `max` and `integer`. In the HTML each becomes a slider plus a number box. `fanout`, `duration_s` and `timeout_s` are editable too when they are numbers.

**Formulas.** `value`, `demand`, `baseline`, `fanout`, `duration_s` and `timeout_s` can each be a number or a formula string. A formula can use:
- numbers and `+ - * /`
- `min() max() ceil() floor() round()`
- `load` (incoming req/s)
- any global
- the component's own params and built-ins, by bare name
- another component's values, as `<id>.<name>`. Built-ins on every component are `fanout`, `duration_s`, `timeout_s`, `rps` (= load × fanout) and `concurrency` (= rps × duration_s).

Limit `type` sets the default `demand` when none is given:
- `rps`: rps
- `concurrency`: concurrency
- `connections`: concurrency of `held_by` × `per_holder`, else own concurrency
- `throughput`: rps × `unit_size`

Use `demand` to override it. For example, a stream consumer's concurrency is `stream.shards * parallelization_factor`, regardless of load.

Other rules:
- A limit whose value works out to 0 or less is **off**, e.g. reserved concurrency set to 0.
- Limits with the same `shared_id` draw on one pool. Their demands add up against the first member's `value`, and `baseline` is usage by callers outside the model.
- The break point is found numerically: the load at which utilization reaches 100%. This works with any formula, provided utilization doesn't fall as load rises.
- `connects_to` takes ids or names and draws the graph. Without it, the array order is drawn as a chain.
- `kind` labels the box. `async: true` excludes a consumer from the caller-timeout check, which runs along `connects_to`.
- `fixes[].set` keys are `<id>.<param>`, `<id>.fanout|duration_s|timeout_s`, or a global name. The HTML's "Try it" button applies them.
- `fixes[].quota` adds a row to the quota-request table.
- `checked` holds the date a limit was verified.
- `load_unit` (e.g. "uploads/s", "orders/s") labels the load everywhere; default "req/s". `default_scenario` picks the scenario the page opens on; otherwise `peak`, then `target`, then the second scenario.
- `checks`: rules that aren't limits, as `{ "name", "expr", "min"?, "max"?, "unit"?, "failure" }`. The formula is evaluated at the current load and must stay within min/max. Use it for SQS visibility ≥ 6× the function timeout, queue delay after a spike, scale-up time, timeout budgets, cost ceilings and so on. Checks appear in the HTML's Rule checks table and in the calculator output.

## Mandatory capacity checks (copy into checklist.md)
- [ ] C1 Every limit in the request path has a source + date, and is marked hard or adjustable
- [ ] C2 Shared limits include all other consumers (account-wide concurrency, shared DB, shared API keys)
- [ ] C3 Break point of every component ≥ target peak × 1.3 (30% headroom)
- [ ] C4 Burst: scaling rate / burst bucket / cold start handles the spike scenario
- [ ] C5 Connections: compute concurrency × pool size ≤ DB/cache max connections (or a proxy/pooler is in place)
- [ ] C6 Timeouts decrease downstream; no component's duration is close to its timeout
- [ ] C7 Over-limit behaviour is defined for every component: queued, shed with a clear error, or retried with backoff + jitter. Never silent loss.
- [ ] C8 Retries are bounded; no retry storm (check SDK default retries × layers)
- [ ] C9 Async paths have a DLQ / failure destination, plus an alarm on it
- [ ] C10 Third-party rate limits are modelled, with a client-side limiter or queue in front
- [ ] C11 Hot-key / per-partition limits checked against realistic skew
- [ ] C12 Alarms exist on throttles, errors, queue age, and connection count, at the 70% utilization level
- [ ] C13 Cost at the peak and spike scenarios is within budget (or budget not given → reported)
- [ ] C14 Quota increase requests listed for the user (never filed by the agent)

## Mitigations (pick by failure type)
| Problem | Typical fixes |
|---|---|
| Compute concurrency cap | Reserved concurrency per function (protects others), provisioned concurrency for bursts, a quota increase, a queue in front to smooth the load |
| DB connection exhaustion | RDS Proxy / PgBouncer, a smaller per-instance pool, reserved concurrency to cap callers, moving reads to a cache or replica |
| Gateway / API throttle | Usage plans, caching, a quota increase, a CDN for GETs |
| Spike faster than scaling | Queue + workers, provisioned/min instances, pre-warming before known events |
| Third-party rate limit | A client-side token bucket, a queue, batching, caching responses, multiple keys only if the provider's ToS allows it |
| Hot partition | Better key design, write sharding, caching hot reads |
| Long sync calls (LLM, reports) | Make them async: queue + status polling or a webhook |
| Retry storm | Backoff with jitter, a retry budget, circuit breaker, idempotency keys |
