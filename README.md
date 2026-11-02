# Order Book Replay Lab (P10)

**What it proves:** deterministic reconstruction of a synthetic level-2 book from an initial snapshot and ordered updates; sequence-gap fail-closed behavior; bid–ask, imbalance, depth VWAP and simulated latency-aware marketable-buy execution costs.

**What it does NOT prove:** real HFT execution, exchange gateway performance, profitable trading, priority in the order queue, live data quality or realistic matching-engine performance.

## Run

Python 3.10+; stdlib only.

```bash
python -m unittest discover -v
python demo.py
```

## Measured synthetic experiment

- 600 generated delta messages after a seeded snapshot; 24/24 unit tests PASS.
- 54 decision timestamps × four simulated latencies = **216 hypothetical marketable buys**.
- Buy size: 2 units. Assumed taker fee: 5 basis points. Decision benchmark: original midprice at signal time. No realized PnL.

| Arrival latency | Mean execution cost (includes 5 bps fee) |
|---|---:|
| 0 ms | 6.2392 bps |
| 20 ms | 6.28186 bps |
| 100 ms | 7.57544 bps |
| 500 ms | 12.49767 bps |

**This pattern is an outcome of one chosen synthetic upward-biased price path, not an empirical latency-cost law.** Prices, liquidity, volumes, arrival times and fees are all artificial assumptions.

## Implementation

`generate` → labeled synthetic snapshot and deltas → `Book.snapshot` and `Book.apply` → integrity checks (`SequenceGap`, crossed book, negative quantities, stale states) → `Book.execute` VWAP → `measure_latency` samples → CSV/JSON/PNG.

Book event IDs model the idea of contiguous update coverage; the generated data is **not** a verbatim Binance WebSocket schema. A live Binance local-book adapter would additionally need documented snapshot buffering, synchronization, stale-feed detection, venue-specific reconnect rules, precise timestamps and throttling.

### Limitations

- Full-depth changes from a *fabricated* price process are not empirical L2 market structure.
- No order placement, private fill messages, queue reconstruction, cancels/trades differentiation, adverse selection from actual order flow, hidden liquidity, network jitter or trading API.
- No maker/taker rebates or funding (taker fee assumption only); no market impact beyond consuming displayed synthetic depth.
- Markout is a simulated post-fill price difference, not a trade return.

## Files

- `orderbook.py`: decimal-price L2 snapshot/delta algorithm, integrity, VWAP, synthetic generator.
- `demo.py`, `test_orderbook.py`.
- `results/synthetic_depth_feed.jsonl`: explicitly labeled `SYNTHETIC` in every message.
- `results/execution_samples.csv`, `results/summary.json`, `results/latency_cost.png`.

## Next milestones

Implement and separately validate a documented live-data-only adapter for Binance or Coinbase (no trading permissions); test disconnections, out-of-order / missing messages, microsecond clocks, archived ground truth and real capture-vs-replay latency; only then evaluate hypotheses against real market data.

## Reference

- https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md

Independent synthetic research artifact; exchange rules must be independently verified before any real use.
