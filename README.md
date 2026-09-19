# hermes-kalshi

Custom [Hermes Agent](https://hermes-agent.nousresearch.com) skills for **live Kalshi operations**.

This is not the matching engine. Trading execution stays in the Bogachka stack (`kalshi_state`, `kalshi_runner`). These packages teach a Hermes instance (operator on the live host) how to **read** Redis — health, current windows, executable BBO — without printing secrets.

## Layout

```
skills/lilly-redis/          Hermes skill package
  SKILL.md
  scripts/health.py          process-level kalshi_state health
  scripts/windows.py         current events from lifecycle + quote ages
  scripts/quotes.py          15m BBO + hourly ATM (k=1, live spot)
  tests/test_strike.py       lockstep with kalshi_state strike_util.rs
```

## Install (Hermes)

```bash
git clone git@github.com:sweet-tree/hermes-kalshi.git
mkdir -p ~/.hermes/skills/devops
ln -sfn "$(pwd)/hermes-kalshi/skills/lilly-redis" ~/.hermes/skills/devops/lilly-redis
```

Scripts read Redis on the live host and never print secrets. They belong on that host, not a laptop.

## License

MIT
