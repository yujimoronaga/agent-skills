# Capacity Report — <system name>

_Date: <date> · Mode: review only | full loop · Council rounds: <n>_

## TL;DR
**It breaks first at <component> — <limit> (<value>, hard|adjustable). Break point: ~<X> req/s; your peak target is <Y> req/s.**
When this happens, users see <429s / timeouts / lost messages / slow pages>.

## Request path
```
Client → <component> → <component> → <component>
                      └→ <async branch> → <component>
```

## Scenarios
| Scenario | Incoming req/s | Source |
|---|---|---|
| expected | | intake Q4 / assumption |
| peak | | intake Q5 |
| spike | | intake Q6 |

## Break-point ranking (weakest first)
| # | Component | Limit | Value | Hard/Adj | Verified | Util @ peak | Breaks at (req/s) | Failure mode |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | ✅ source / ❌ | | | |

## Chain checks
- Timeouts (upstream → downstream): <…> — OK / mismatch
- Connections: <compute concurrency × pool> vs <max_connections>
- Burst: <spike shape> vs <scaling rate / burst bucket>
- Retries: <layers × SDK retries> → amplification <×n>

## Fixes
| # | Fixes breakpoint | Type | Change | Effort | Cost impact | New break point |
|---|---|---|---|---|---|---|
| 1 | #1 | quota / config / code / redesign | | S/M/L | | |

## Quota increase requests (for you to file)
| Service | Quota | Current | Request | Justification |
|---|---|---|---|---|

## Results (Stage 4)
| Target | Measured | Result | Evidence |
|---|---|---|---|
Predicted first breakpoint vs observed: <…>

## Open risks / unverified limits
- …
