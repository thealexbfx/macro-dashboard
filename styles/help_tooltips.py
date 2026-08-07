from __future__ import annotations

import streamlit as st


def inject_help_tooltip_css() -> None:
    st.markdown(
        """
        <style>
        .ml-help-label {
            display: inline !important;
        }

        .ml-help-anchor {
            position: relative !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;

            width: 15px;
            height: 15px;
            flex: 0 0 15px;

            margin-left: 0.28rem;
            padding: 0;

            vertical-align: 0.08em;
            cursor: help;
            outline: none;
        }

        .ml-help-icon {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;

            width: 15px !important;
            height: 15px !important;
            min-width: 15px !important;
            flex: 0 0 15px !important;

            margin: 0 !important;
            padding: 0 !important;

            border: 1px solid #9aabba !important;
            border-radius: 50% !important;
            background: #ffffff !important;

            color: #607086 !important;
            font-family: inherit !important;
            font-size: 0.62rem !important;
            font-weight: 800 !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
        }

        .ml-help-tooltip {
            position: absolute !important;
            z-index: 10000 !important;

            left: 50% !important;
            right: auto !important;
            bottom: calc(100% + 9px) !important;
            top: auto !important;

            display: block !important;
            width: 230px !important;
            min-width: 230px !important;
            height: auto !important;

            margin: 0 !important;
            padding: 0.65rem 0.75rem !important;

            border: 1px solid #cfd8e3 !important;
            border-radius: 8px !important;
            background: #10233f !important;

            color: #ffffff !important;
            font-family: inherit !important;
            font-size: 0.74rem !important;
            font-weight: 500 !important;
            line-height: 1.45 !important;
            letter-spacing: normal !important;
            text-align: left !important;
            text-transform: none !important;
            white-space: normal !important;

            box-shadow:
                0 10px 24px rgba(15, 35, 63, 0.18) !important;

            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;

            transform: translateX(-50%) !important;

            transition:
                opacity 120ms ease,
                transform 120ms ease,
                visibility 120ms ease;
        }

        .ml-help-tooltip::after {
            content: "";
            position: absolute;

            top: 100%;
            left: 50%;
            transform: translateX(-50%);

            width: 0;
            height: 0;

            border-width: 6px;
            border-style: solid;
            border-color:
                #10233f transparent transparent transparent;
        }

        .ml-help-anchor:hover .ml-help-tooltip,
        .ml-help-anchor:focus .ml-help-tooltip,
        .ml-help-anchor:focus-within .ml-help-tooltip {
            opacity: 1 !important;
            visibility: visible !important;
            transform:
                translateX(-50%) translateY(-2px) !important;
        }

        /*
        Prevent Macro Engine cards from clipping the tooltip.
        */
        .ml-environment-hero,
        .ml-environment-name,
        .ml-card,
        .ml-card-label {
            overflow: visible !important;
        }

        .ml-card-label .ml-help-anchor {
            display: inline-flex !important;
            margin-left: 0.24rem;
        }

        /*
        Keep the tooltip attached to the environment label while
        avoiding excessive horizontal overflow.
        */
        .ml-environment-name .ml-help-anchor {
            display: inline-flex !important;
            vertical-align: 0.14em;
        }

        @media (max-width: 700px) {
            .ml-help-tooltip {
                position: fixed !important;

                left: 50% !important;
                right: auto !important;
                bottom: 24px !important;
                top: auto !important;

                width: min(
                    280px,
                    calc(100vw - 40px)
                ) !important;

                min-width: 0 !important;
                max-width: calc(100vw - 40px) !important;

                transform: translateX(-50%) !important;
            }

            .ml-help-tooltip::after {
                display: none !important;
            }

            .ml-help-anchor:hover .ml-help-tooltip,
            .ml-help-anchor:focus .ml-help-tooltip,
            .ml-help-anchor:focus-within .ml-help-tooltip {
                transform: translateX(-50%) !important;
            }
        }
        .ml-pillar-card,
        .ml-pillar-name,
        .ml-pillar-label,
        .ml-pillar-footer {
            overflow: visible !important;
        }

        .ml-pillar-name .ml-help-anchor,
        .ml-pillar-label .ml-help-anchor,
        .ml-pillar-footer .ml-help-anchor {
            display: inline-flex !important;
            margin-left: 0.22rem;
        }

        .ml-pillar-footer .ml-help-icon {
            width: 13px !important;
            height: 13px !important;
            min-width: 13px !important;
            flex-basis: 13px !important;
            font-size: 0.55rem !important;
        }
        .ml-pillar-card:first-child .ml-help-tooltip {
            left: -6px !important;
            transform: none !important;
        }

        .ml-pillar-card:first-child .ml-help-tooltip::after {
            left: 12px !important;
            transform: none !important;
        }

        .ml-pillar-card:last-child .ml-help-tooltip {
            left: auto !important;
            right: -6px !important;
            transform: none !important;
        }

        .ml-pillar-card:last-child .ml-help-tooltip::after {
            left: auto !important;
            right: 12px !important;
            transform: none !important;
        }
        /* Macro Engine evidence tooltips */
        .ml-evidence-panel,
        .ml-evidence-panel-header,
        .ml-driver-table,
        .ml-driver-row,
        .ml-driver-main,
        .ml-driver-stat,
        .ml-driver-stat-label {
            overflow: visible !important;
        }
        .ml-evidence-panel-title .ml-help-tooltip {
            top: calc(100% + 9px) !important;
            bottom: auto !important;
        }

        .ml-evidence-panel-title .ml-help-tooltip::after {
            top: auto !important;
            bottom: 100% !important;

            border-color:
                transparent transparent #10233f transparent !important;
        }

        .ml-evidence-panel-title
        .ml-help-anchor:hover
        .ml-help-tooltip,
        .ml-evidence-panel-title
        .ml-help-anchor:focus
        .ml-help-tooltip,
        .ml-evidence-panel-title
        .ml-help-anchor:focus-within
        .ml-help-tooltip {
            transform:
                translateX(-50%) translateY(2px) !important;
        }
        .ml-history-stat:last-child .ml-help-tooltip {
            left: auto !important;
            right: -6px !important;
            transform: none !important;
        }

        .ml-history-stat:last-child .ml-help-tooltip::after {
            left: auto !important;
            right: 10px !important;
            transform: none !important;
        }

        .ml-history-stat:last-child
        .ml-help-anchor:hover
        .ml-help-tooltip,
        .ml-history-stat:last-child
        .ml-help-anchor:focus
        .ml-help-tooltip,
        .ml-history-stat:last-child
        .ml-help-anchor:focus-within
        .ml-help-tooltip {
            transform: translateY(-2px) !important;
        }
        /* Validation metric tooltips */
        .ml-validation-metric,
        .ml-history-metric,
        .ml-history-metric-label,
        .ml-validation-assessment,
        .ml-current-regime-grid,
        .ml-current-regime-item,
        .ml-current-regime-item-label {
            overflow: visible !important;
        }

        .ml-history-metric-label .ml-help-anchor,
        .ml-current-regime-item-label .ml-help-anchor {
            display: inline-flex !important;
            margin-left: 0.22rem;
        }

        /* Rightmost metric cards should open tooltips leftward */
        div[data-testid="stHorizontalBlock"]
            > div:last-child
            .ml-validation-metric
            .ml-help-tooltip {
            left: auto !important;
            right: -6px !important;
            transform: none !important;
        }

        div[data-testid="stHorizontalBlock"]
            > div:last-child
            .ml-validation-metric
            .ml-help-tooltip::after {
            left: auto !important;
            right: 10px !important;
            transform: none !important;
        }

        div[data-testid="stHorizontalBlock"]
            > div:last-child
            .ml-validation-metric
            .ml-help-anchor:hover
            .ml-help-tooltip,
        div[data-testid="stHorizontalBlock"]
            > div:last-child
            .ml-validation-metric
            .ml-help-anchor:focus
            .ml-help-tooltip {
            transform: translateY(-2px) !important;
        }
        /* Historical Regime Explorer tooltips */
        .hre-regime-summary,
        .hre-regime-summary-top,
        .hre-regime-count,
        .hre-metric-card,
        .hre-metric-label,
        .hre-asset-summary,
        .hre-asset-summary-heading,
        .hre-asset-summary-horizon,
        .hre-asset-summary-grid,
        .hre-asset-summary-metric,
        .hre-entry-card,
        .hre-entry-card-body,
        .hre-entry-row,
        .hre-entry-row span {
            overflow: visible !important;
        }

        .hre-metric-label .ml-help-anchor,
        .hre-asset-summary-horizon .ml-help-anchor,
        .hre-asset-summary-metric .ml-help-anchor,
        .hre-entry-row .ml-help-anchor,
        .hre-regime-count .ml-help-anchor {
            display: inline-flex !important;
            margin-left: 0.22rem;
        }
        .hre-asset-summary-metric:last-child .ml-help-tooltip {
            left: auto !important;
            right: -6px !important;
            transform: none !important;
        }

        .hre-asset-summary-metric:last-child .ml-help-tooltip::after {
            left: auto !important;
            right: 10px !important;
            transform: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )