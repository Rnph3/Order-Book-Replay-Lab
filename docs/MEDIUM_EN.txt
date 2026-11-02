# Latency Is a Price Assumption: Replaying a Synthetic Limit Order Book

*Snapshot recovery, ordered updates, taker VWAP, and why an offline execution-cost chart is not evidence of a trading edge.*

There is a large difference between evaluating a trading signal on a candle and evaluating an order sent to an exchange. A candle does not tell you which price levels had enough displayed quantity, whether the order book was stale, or which quote arrived before your order.

I built **Order Book Replay Lab** to study the data-engineering and accounting side of that gap.

## Start with integrity, not alpha

The lab reconstructs a level-2 book from an initial snapshot and subsequent depth updates. It validates monotonic update coverage, rejects crossed books, detects negative sizes and invalid quotes, and refuses to quote or execute on a book marked stale after a sequence gap.

Those checks are inspired by the exchange documentation for maintaining a local depth book. They are not a complete implementation of any venue's real-time feed handler.

The experiment uses **600 deterministically generated synthetic update messages**. Every dataset row is explicitly marked `SYNTHETIC`. No exchange market data was captured.

## How a simulated marketable order is priced

I implemented a depth-consuming VWAP function. Given a requested buy size, it walks ask levels from best to worse until enough displayed quantity is consumed. It rejects a request larger than available synthetic depth.

A synthetic decision is made at time `t` using the midpoint, while the hypothetical order executes against the first reconstructed book at `t + latency`.

Execution cost is calculated in basis points against the **original decision-time midpoint**, plus an assumed 5 bps taker fee. It captures movement in this simulated quote path and synthetic order-book walking. It does not capture hidden liquidity, actual fills, queue priority, networking, cancel/replace behavior, or realized PnL.

## Results

For 54 decision times and four hypothetical latencies, the lab evaluated **216 buy executions** of two units each:

- **0 ms:** 6.2392 bps mean execution cost
- **20 ms:** 6.28186 bps
- **100 ms:** 7.57544 bps
- **500 ms:** 12.49767 bps

The code passed **24/24 unit tests**.

*[Insert `results/latency_cost.png` here.]*

In this particular *upward-biased simulated price path*, longer delays increased the average measured buy cost. This is not a universal empirical relation. Change the generator, side of trade, book depth, fee assumption or signal timing and the numbers can change markedly.

## The important limit

An L2 aggregate feed generally cannot tell you an individual limit order's precise position in a matching-engine queue. A passive-fill simulator that silently assumes FIFO priority from top-of-book data can easily overstate fill probability.

For that reason this release models only immediate taker VWAP. It does not claim to solve queue reconstruction or high-frequency trading execution.

## Next step

A useful upgrade is a read-only live feed adapter that implements an exchange's exact snapshot/delta synchronization and reconnect specification. I would compare archived raw depth events against reconstructed best quotes, then evaluate event-time versus receive-time jitter, latency, realistic fees, and market impact over independent real-data periods.

**Code and synthetic reproducible evidence:** [INSERT VERIFIED PUBLIC GITHUB URL]

**Scope:** Deterministic educational market-microstructure simulation; no live data or profitable strategy claimed.

Reference: [Binance Spot WebSocket depth stream documentation](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)

**Medium Topics:** Algorithmic Trading · Quantitative Finance · Cryptocurrency · Python · Data Engineering
