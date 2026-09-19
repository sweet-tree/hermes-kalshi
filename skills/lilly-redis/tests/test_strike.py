#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from strike import (  # noqa: E402
    event_ticker_of,
    parse_price_live,
    parse_strike,
    select_nearest_market_tickers,
    spot_for_event_ticker,
)


class StrikeTests(unittest.TestCase):
    def test_parse_strike_ladder_vs_updown(self):
        self.assertEqual(parse_strike("KXBTCD-26JUN1200-T63499.99"), 63499.99)
        self.assertIsNone(parse_strike("KXBTC15M-26JUN121545-45"))

    def test_event_ticker_of(self):
        self.assertEqual(event_ticker_of("KXBTCD-26JUN1205-T63299.99"), "KXBTCD-26JUN1205")
        self.assertEqual(event_ticker_of("KXETHD-26MAY3106-T1699.99"), "KXETHD-26MAY3106")
        self.assertEqual(event_ticker_of("KXBTC15M-26JUN121815-15"), "KXBTC15M-26JUN121815")

    def test_select_nearest_uses_live_spot(self):
        tickers = [
            "KXBTCD-TEST-T74799.99",
            "KXBTCD-TEST-T73499.99",
            "KXBTCD-TEST-T73599.99",
            "KXBTCD-TEST-T73699.99",
            "KXBTCD-TEST-T76099.99",
        ]
        got = select_nearest_market_tickers(tickers, 3, 73500.0)
        self.assertEqual(
            got,
            [
                "KXBTCD-TEST-T73499.99",
                "KXBTCD-TEST-T73599.99",
                "KXBTCD-TEST-T73699.99",
            ],
        )

    def test_select_nearest_k1_is_atm(self):
        tickers = [
            "KXBTCD-TEST-T81199.99",
            "KXBTCD-TEST-T80799.99",
            "KXBTCD-TEST-T81299.99",
        ]
        # |81299.99-81264.79| < |81199.99-81264.79|
        self.assertEqual(
            select_nearest_market_tickers(tickers, 1, 81264.79),
            ["KXBTCD-TEST-T81299.99"],
        )

    def test_no_spot_no_median(self):
        tickers = ["KXBTCD-TEST-T1.0", "KXBTCD-TEST-T2.0", "KXBTCD-TEST-T3.0"]
        self.assertEqual(select_nearest_market_tickers(tickers, 1, None), [])

    def test_price_live_split(self):
        self.assertAlmostEqual(parse_price_live(b"81264.79:123"), 81264.79)
        self.assertIsNone(parse_price_live(None))

    def test_spot_for_event(self):
        self.assertEqual(spot_for_event_ticker("KXBTCD-26SEP1920", 1.0, 2.0), 1.0)
        self.assertEqual(spot_for_event_ticker("KXETHD-26SEP1920", 1.0, 2.0), 2.0)
        self.assertIsNone(spot_for_event_ticker("KXBTC15M-26SEP191945", 1.0, 2.0))


if __name__ == "__main__":
    unittest.main()
