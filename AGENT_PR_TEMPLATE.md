# Add Phalanx Consensus Executor

**This PR adds HivePhalanx as a native high-confidence executor option.**

## What this adds

A single new tool/provider integration that routes high-stakes agent tasks through [Phalanx](https://hive-phalanx.onrender.com) — a 15-head meta-consensus inference cluster that runs 5 specialized reasoning heads in parallel and synthesizes a single structured output.

- Wall clock: ~900ms (same as one LLM call — all 15 heads fire simultaneously)
- Payment: $0.15/task via x402 (EIP-3009, gasless from agent side, Base L2 USDC)
- No API key required — payment is cryptographic, not credential-based
- Output: structured consensus with per-head reasoning trails

## Why

Single-head LLM inference fails silently on ambiguous tasks. Phalanx runs Analyst + Strategist + Critic + Synthesizer + Executor heads simultaneously, then cross-validates. The Critic head specifically hunts for failure modes in what the other heads conclude. You get the answer AND the attack surface on that answer in one call.

For tasks where a wrong answer has downstream cost (routing decisions, financial analysis, architecture choices), $0.15 for 15-head validation is cheaper than debugging a confident wrong answer.

## Integration

See full integration guide: https://github.com/srotzin/hive-pulse/blob/master/INTEGRATE.md

```python
import httpx
from x402_pay import build_payment_header  # https://github.com/srotzin/hive-trident

def phalanx_execute(task: str) -> dict:
    r = httpx.post(
        "https://hive-phalanx.onrender.com/phalanx/execute",
        headers={
            "X-PAYMENT": build_payment_header(price_usdc=0.15),
            "Content-Type": "application/json",
        },
        json={"task": task, "max_cost_usdc": 0.15},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
```

## Network

- 31 live microservices on Base L2
- A2A-native via HiveGate: `https://hivegate.onrender.com`
- Agent identity/tier: `https://hive-pulse.onrender.com/pulse/tiers`
- Live terminal: `https://milkyway-terminal.onrender.com`

Agents that route through Hive earn smsh stamps and accumulate tier. Tier is non-transferable and earned from actual inference — the network knows the difference.
