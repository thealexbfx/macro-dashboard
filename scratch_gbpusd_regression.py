from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import (
    variance_inflation_factor,
)


DATA_PATH = Path(
    "gbpusd_relative_macro_last_60_months.csv"
)

FORWARD_HORIZONS = [
    "gbpusd_forward_1m",
    "gbpusd_forward_3m",
]

LEVEL_FEATURES = [
    "us_activity",
    "uk_activity",
    "us_inflation",
    "uk_inflation",
    "us_financial",
    "uk_financial",
]

RELATIVE_FEATURES = [
    "activity_difference",
    "inflation_difference",
    "financial_difference",
]


def standardize_features(
    data: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """
    Standardize predictors so coefficients can be compared directly.

    A coefficient represents the change in forward GBP/USD return
    associated with a one-standard-deviation increase in that signal.
    """
    standardized = data[feature_columns].copy()

    for column in feature_columns:
        standard_deviation = standardized[column].std(ddof=0)

        if (
            pd.isna(standard_deviation)
            or standard_deviation == 0
        ):
            raise ValueError(
                f"{column} has no usable variation."
            )

        standardized[column] = (
            standardized[column]
            - standardized[column].mean()
        ) / standard_deviation

    return standardized


def calculate_vif(
    standardized_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate variance inflation factors.

    Large VIF values suggest that predictors contain overlapping
    information and coefficients may therefore be unstable.
    """
    matrix = sm.add_constant(
        standardized_features,
        has_constant="add",
    )

    rows = []

    for index, column in enumerate(matrix.columns):
        if column == "const":
            continue

        rows.append(
            {
                "feature": column,
                "vif": variance_inflation_factor(
                    matrix.values,
                    index,
                ),
            }
        )

    return pd.DataFrame(rows).sort_values(
        "vif",
        ascending=False,
    )


def fit_macro_regression(
    data: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    model_name: str,
) -> tuple[
    sm.regression.linear_model.RegressionResultsWrapper,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Fit an OLS regression with Newey-West HAC standard errors.

    HAC errors are used because monthly financial returns and macro
    observations may contain serial correlation and changing volatility.
    """
    required_columns = feature_columns + [target_column]

    sample = data[required_columns].dropna().copy()

    standardized_features = standardize_features(
        sample,
        feature_columns,
    )

    design_matrix = sm.add_constant(
        standardized_features,
        has_constant="add",
    )

    target = sample[target_column]

    maximum_lags = 1 if target_column.endswith("1m") else 3

    model = sm.OLS(
        target,
        design_matrix,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": maximum_lags,
        },
    )

    confidence_intervals = model.conf_int()

    coefficient_report = pd.DataFrame(
        {
            "feature": model.params.index,
            "coefficient": model.params.values,
            "standard_error": model.bse.values,
            "t_statistic": model.tvalues.values,
            "p_value": model.pvalues.values,
            "confidence_low": (
                confidence_intervals.iloc[:, 0].values
            ),
            "confidence_high": (
                confidence_intervals.iloc[:, 1].values
            ),
        }
    )

    coefficient_report["model"] = model_name
    coefficient_report["target"] = target_column
    coefficient_report["observations"] = int(
        model.nobs
    )
    coefficient_report["r_squared"] = model.rsquared
    coefficient_report["adjusted_r_squared"] = (
        model.rsquared_adj
    )

    coefficient_report["coefficient_percent"] = (
        coefficient_report["coefficient"] * 100
    )

    vif_report = calculate_vif(
        standardized_features
    )

    vif_report["model"] = model_name
    vif_report["target"] = target_column

    return model, coefficient_report, vif_report


def expanding_window_validation(
    data: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    minimum_training_observations: int = 30,
) -> tuple[pd.DataFrame, dict]:
    """
    Perform an expanding-window out-of-sample test.

    Each prediction is generated using only observations that would
    have been available before the predicted month.
    """
    required_columns = (
        ["month"]
        + feature_columns
        + [target_column]
    )

    sample = (
        data[required_columns]
        .dropna()
        .sort_values("month")
        .reset_index(drop=True)
    )

    predictions = []

    for test_index in range(
        minimum_training_observations,
        len(sample),
    ):
        training = sample.iloc[:test_index].copy()
        testing = sample.iloc[[test_index]].copy()

        training_means = training[
            feature_columns
        ].mean()

        training_standard_deviations = training[
            feature_columns
        ].std(ddof=0)

        valid_standard_deviations = (
            training_standard_deviations
            .replace(0, np.nan)
        )

        x_train = (
            training[feature_columns]
            - training_means
        ) / valid_standard_deviations

        x_test = (
            testing[feature_columns]
            - training_means
        ) / valid_standard_deviations

        if (
            x_train.isna().any().any()
            or x_test.isna().any().any()
        ):
            continue

        x_train = sm.add_constant(
            x_train,
            has_constant="add",
        )

        x_test = sm.add_constant(
            x_test,
            has_constant="add",
        )

        model = sm.OLS(
            training[target_column],
            x_train,
        ).fit()

        prediction = float(
            model.predict(x_test).iloc[0]
        )

        actual = float(
            testing[target_column].iloc[0]
        )

        predictions.append(
            {
                "month": testing["month"].iloc[0],
                "target": target_column,
                "actual_return": actual,
                "predicted_return": prediction,
                "actual_direction": np.sign(actual),
                "predicted_direction": np.sign(
                    prediction
                ),
                "correct_direction": (
                    np.sign(actual)
                    == np.sign(prediction)
                ),
                "squared_error": (
                    actual - prediction
                ) ** 2,
            }
        )

    prediction_report = pd.DataFrame(predictions)

    if prediction_report.empty:
        return prediction_report, {
            "oos_observations": 0,
            "directional_accuracy": np.nan,
            "rmse": np.nan,
            "prediction_correlation": np.nan,
        }

    summary = {
        "oos_observations": len(prediction_report),
        "directional_accuracy": (
            prediction_report[
                "correct_direction"
            ].mean()
        ),
        "rmse": np.sqrt(
            prediction_report[
                "squared_error"
            ].mean()
        ),
        "prediction_correlation": (
            prediction_report[
                [
                    "actual_return",
                    "predicted_return",
                ]
            ]
            .corr()
            .iloc[0, 1]
        ),
    }

    return prediction_report, summary


def print_regression_result(
    model_name: str,
    target_column: str,
    model,
    coefficients: pd.DataFrame,
    vif_report: pd.DataFrame,
) -> None:
    print("\n" + "=" * 110)
    print(
        f"{model_name.upper()} — "
        f"{target_column.upper()}"
    )
    print("=" * 110)

    print(
        f"Observations:       {int(model.nobs)}\n"
        f"R-squared:          {model.rsquared:.3f}\n"
        f"Adjusted R-squared: "
        f"{model.rsquared_adj:.3f}\n"
        f"Model p-value:      "
        f"{model.f_pvalue:.4f}"
    )

    display = coefficients.loc[
        coefficients["feature"] != "const",
        [
            "feature",
            "coefficient_percent",
            "standard_error",
            "t_statistic",
            "p_value",
            "confidence_low",
            "confidence_high",
        ],
    ].copy()

    display = display.sort_values(
        "coefficient_percent",
        key=lambda values: values.abs(),
        ascending=False,
    )

    print(
        "\nSTANDARDIZED COEFFICIENTS\n"
        "Coefficient = percentage-point GBP/USD return associated "
        "with a one-standard-deviation increase in the signal."
    )

    print(
        display.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}",
        )
    )

    print("\nMULTICOLLINEARITY CHECK")

    print(
        vif_report[
            [
                "feature",
                "vif",
            ]
        ].to_string(
            index=False,
            float_format=lambda value: f"{value:.2f}",
        )
    )


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {DATA_PATH}. "
            "Run scratch_gbpusd_correlation.py first."
        )

    research = pd.read_csv(DATA_PATH)

    research["month"] = research[
        "month"
    ].astype(str)

    missing_columns = [
        column
        for column in (
            LEVEL_FEATURES
            + RELATIVE_FEATURES
            + FORWARD_HORIZONS
        )
        if column not in research.columns
    ]

    if missing_columns:
        raise ValueError(
            "The research CSV is missing these columns: "
            + ", ".join(missing_columns)
        )

    coefficient_reports = []
    vif_reports = []
    out_of_sample_reports = []
    out_of_sample_summaries = []

    specifications = [
        (
            "Country-level macro model",
            LEVEL_FEATURES,
        ),
        (
            "Relative macro model",
            RELATIVE_FEATURES,
        ),
    ]

    for model_name, features in specifications:
        for target_column in FORWARD_HORIZONS:
            model, coefficient_report, vif_report = (
                fit_macro_regression(
                    research,
                    feature_columns=features,
                    target_column=target_column,
                    model_name=model_name,
                )
            )

            print_regression_result(
                model_name=model_name,
                target_column=target_column,
                model=model,
                coefficients=coefficient_report,
                vif_report=vif_report,
            )

            coefficient_reports.append(
                coefficient_report
            )

            vif_reports.append(vif_report)

            predictions, summary = (
                expanding_window_validation(
                    research,
                    feature_columns=features,
                    target_column=target_column,
                    minimum_training_observations=30,
                )
            )

            if not predictions.empty:
                predictions["model"] = model_name

                out_of_sample_reports.append(
                    predictions
                )

            out_of_sample_summaries.append(
                {
                    "model": model_name,
                    "target": target_column,
                    **summary,
                }
            )

    all_coefficients = pd.concat(
        coefficient_reports,
        ignore_index=True,
    )

    all_vif = pd.concat(
        vif_reports,
        ignore_index=True,
    )

    out_of_sample_summary = pd.DataFrame(
        out_of_sample_summaries
    )

    print("\n" + "=" * 110)
    print("EXPANDING-WINDOW OUT-OF-SAMPLE RESULTS")
    print("=" * 110)

    summary_display = out_of_sample_summary.copy()

    summary_display["directional_accuracy"] = (
        summary_display["directional_accuracy"]
        * 100
    )

    summary_display["rmse"] = (
        summary_display["rmse"] * 100
    )

    print(
        summary_display.to_string(
            index=False,
            float_format=lambda value: f"{value:.2f}",
        )
    )

    all_coefficients.to_csv(
        "gbpusd_regression_coefficients.csv",
        index=False,
    )

    all_vif.to_csv(
        "gbpusd_regression_vif.csv",
        index=False,
    )

    out_of_sample_summary.to_csv(
        "gbpusd_regression_oos_summary.csv",
        index=False,
    )

    if out_of_sample_reports:
        pd.concat(
            out_of_sample_reports,
            ignore_index=True,
        ).to_csv(
            "gbpusd_regression_oos_predictions.csv",
            index=False,
        )

    print(
        "\nSaved:\n"
        "  gbpusd_regression_coefficients.csv\n"
        "  gbpusd_regression_vif.csv\n"
        "  gbpusd_regression_oos_summary.csv\n"
        "  gbpusd_regression_oos_predictions.csv"
    )


if __name__ == "__main__":
    main()