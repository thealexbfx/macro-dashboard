import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

from macro_engine.research.analytics import (
    SeriesMetadata,
    align,
    analyze,
    changes,
    metadata,
    relationship,
)


def data(values, dates=None):
    return pd.DataFrame(
        {
            "date": dates
            if dates is not None
            else pd.date_range("2020-01-01", periods=len(values), freq="MS"),
            "value": values,
        }
    )


PRICE = SeriesMetadata(
    category="Equities",
    units="USD",
    frequency="monthly",
    representation="price",
    can_be_nonpositive=False,
    ratio_group="USD-price",
)
RATE = SeriesMetadata(units="%", representation="rate")
YIELD = replace(RATE, representation="yield")


class AnalyticsTests(unittest.TestCase):
    def test_positive_price_modes(self):
        a, b = data([100, 110, 88, 132]), data([100, 100, 100, 100])
        expected = {
            "Price": 132,
            "Percentage Change": 32,
            "Relative Performance": 32,
            "Ratio": 1.32,
            "Drawdown": 0,
        }
        for category in ("Equities", "FX", "Commodities"):
            meta = replace(PRICE, category=category)
            for mode, last in expected.items():
                out, _ = analyze(a, b, meta, meta, mode)
                self.assertAlmostEqual(out.iloc[-1, 0], last)
        out, _ = analyze(a, b, PRICE, PRICE, "Drawdown")
        self.assertAlmostEqual(out.iloc[2, 0], -20)

    def test_rates_and_growth_are_differences(self):
        for representation in ("rate", "growth_rate", "level"):
            meta = replace(RATE, representation=representation)
            np.testing.assert_allclose(
                changes(pd.Series([2.0, 3.0, -1.0, 0.0]), meta).iloc[1:], [1, -4, 1]
            )
            for mode in ("Percentage Change", "Relative Performance", "Drawdown"):
                with self.assertRaises(ValueError):
                    analyze(data([2, 3, 4]), data([1, 2, 3]), meta, meta, mode)

    def test_real_and_nominal_yields_basis_points(self):
        for values in ([4, 4.25, 4.0], [-1, -0.5, 0]):
            out, _ = analyze(
                data(values), data([0, 0, 0]), YIELD, YIELD, "Yield Spread"
            )
            self.assertAlmostEqual(out.iloc[-1, 0], values[-1] * 100)
        np.testing.assert_allclose(
            changes(pd.Series([-1.0, -0.5, 0]), YIELD).iloc[1:], [50, 50]
        )

    def test_index_signed_flows_zero_negative(self):
        index = replace(PRICE, representation="index")
        out, _ = analyze(
            data([100, 120]), data([100, 110]), index, index, "Percentage Change"
        )
        self.assertAlmostEqual(out.iloc[-1, 0], 20)
        for values in ([1, 0, 2], [1, -1, 2]):
            with self.assertRaises(ValueError):
                analyze(
                    data(values), data([1, 2, 3]), PRICE, PRICE, "Percentage Change"
                )
        flow = SeriesMetadata(representation="signed_flow", units="USD")
        np.testing.assert_allclose(
            changes(pd.Series([-10, 0, 10]), flow).iloc[1:], [10, 10]
        )

    def test_ratio_validation(self):
        for meta, denominator in (
            (RATE, [1, 2, 3]),
            (PRICE, [1, 0, 3]),
            (replace(PRICE, units="EUR"), [1, 2, 3]),
        ):
            with self.assertRaises(ValueError):
                analyze(data([1, 2, 3]), data(denominator), PRICE, meta, "Ratio")

    def test_rolling_expected(self):
        a = data([100, 110, 99, 118.8, 130.68])
        out, details = analyze(a, a, PRICE, PRICE, "Rolling Volatility", window=3)
        self.assertAlmostEqual(
            out.iloc[3, 0], np.std([10, -10, 20], ddof=1) * np.sqrt(12)
        )
        self.assertEqual(details["annualization_periods"], 12)
        corr, _ = analyze(a, a, PRICE, PRICE, "Rolling Correlation", window=3)
        self.assertAlmostEqual(corr.iloc[-1, 0], 1)
        _, details = analyze(a, a, PRICE, PRICE, "Rolling Correlation", window=60)
        self.assertEqual(details["valid_statistics"], 0)

    def test_monthly_quarterly_no_exact_date_loss(self):
        a = data(range(6))
        b = data([10, 20], pd.to_datetime(["2020-01-01", "2020-04-01"]))
        frame, details = align(a, b, RATE, replace(RATE, frequency="quarterly"))
        self.assertEqual(details["frequency"], "quarterly")
        np.testing.assert_allclose(frame.left, [2, 5])
        np.testing.assert_allclose(frame.right, [10, 20])

    def test_missing_periods_not_bridged(self):
        a = data([100, 120], pd.to_datetime(["2020-01-01", "2020-03-01"]))
        b = data([1, 2, 3])
        frame, details = align(a, b, PRICE, PRICE)
        self.assertEqual(len(frame), 3)
        self.assertEqual(details["missing_periods"], 1)
        self.assertTrue(changes(frame.left, PRICE).isna().all())

    def test_publication_availability_and_expiry(self):
        a = data([1, 2, 3])
        a["publication_date"] = pd.to_datetime(
            ["2020-02-15", "2020-04-15", "2020-05-15"]
        )
        b = data([4, 5, 6])
        b["publication_date"] = b.date
        frame, _ = align(a, b, RATE, RATE, availability=True, max_age_days=35)
        self.assertTrue(pd.isna(frame.left.iloc[0]))
        self.assertEqual(frame.left.iloc[1], 1)
        self.assertTrue(pd.isna(frame.left.iloc[2]))
        with self.assertRaises(ValueError):
            align(data([1]), data([1]), RATE, RATE, availability=True, max_age_days=30)

    def test_daily_weekly_alignment(self):
        dates = pd.date_range("2020-01-01", periods=21)
        frame, details = align(
            data(range(21), dates),
            data([1, 2, 3], dates[[2, 9, 16]]),
            replace(RATE, frequency="daily"),
            replace(RATE, frequency="weekly"),
        )
        self.assertEqual(details["frequency"], "weekly")
        self.assertEqual(len(frame), 3)

    def test_duplicate_dates_rejected(self):
        a = data([1, 2], pd.to_datetime(["2020-01-01"] * 2))
        with self.assertRaises(ValueError):
            align(a, data([1, 2]), RATE, RATE)

    def test_lead_lag_sign_and_sample(self):
        rng = np.random.default_rng(8)
        x = pd.Series(
            rng.normal(size=80),
            index=pd.date_range("2020-01-01", periods=80, freq="MS"),
        )
        report = relationship(
            pd.DataFrame({"left": x, "right": x.shift(2)}), minimum=12
        )
        hit = next(r for r in report["lead_lag"] if r["lag"] == 2)
        self.assertAlmostEqual(hit["correlation"], 1)
        self.assertEqual(hit["observations"], 78)
        constant = relationship(pd.DataFrame({"left": x * 0, "right": x}))
        self.assertIsNone(constant["full_sample"]["correlation"])

    def test_metadata_adapter(self):
        self.assertEqual(
            metadata({"unit_type": "percent"}, "Wages YoY").representation,
            "growth_rate",
        )
        self.assertEqual(
            metadata({"unit": "percent"}, "Real yield", "Rates & Bonds").representation,
            "yield",
        )
        self.assertFalse(metadata({}, "WTI", "Commodities").return_eligible)


if __name__ == "__main__":
    unittest.main()
