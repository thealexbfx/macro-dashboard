from __future__ import annotations

import streamlit as st


def _inject_home_css() -> None:
    st.markdown(
        """
        <style>
        .ml-home {
            width: 100%;
            max-width: 1120px;
            margin: 0 auto;
            padding-bottom: 3rem;
        }

        /* Hero */

        .ml-home-hero {
            max-width: 850px;
            margin: 1.2rem auto 2rem;
            text-align: center;
        }

        .ml-home-eyebrow {
            color: #52647b;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.075em;
            text-transform: uppercase;
        }

        .ml-home-title {
            margin: 0.45rem 0 0;
            color: #10233f;
            font-size: 2.65rem;
            font-weight: 900;
            letter-spacing: -0.05em;
            line-height: 1.08;
        }

        .ml-home-description {
            max-width: 760px;
            margin: 0.9rem auto 0;
            color: #40536b;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.65;
        }

        .ml-home-positioning {
            max-width: 760px;
            margin: 1rem auto 0;
            padding: 0.8rem 1rem;

            border: 1px solid #d6e0ea;
            border-radius: 9px;
            background: #f7f9fc;

            color: #33465e;
            font-size: 0.86rem;
            line-height: 1.55;
        }

        .ml-home-positioning strong {
            color: #10233f;
        }

        /* Section headings */

        .ml-home-section {
            margin-top: 2.4rem;
        }

        .ml-home-section-header {
            max-width: 780px;
            margin-bottom: 1rem;
        }

        .ml-home-section-title {
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.03em;
        }

        .ml-home-section-description {
            margin-top: 0.3rem;
            color: #52647b;
            font-size: 0.9rem;
            line-height: 1.55;
        }

        /* Framework flow */

        .ml-home-flow {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.65rem;
            margin-top: 1rem;
        }

        .ml-home-flow-step {
            position: relative;
            min-height: 128px;
            padding: 1rem 0.9rem;

            border: 1px solid #d7e0e9;
            border-radius: 11px;
            background: #ffffff;

            box-shadow: 0 3px 12px rgba(15, 35, 63, 0.035);
        }

        .ml-home-flow-number {
            display: flex;
            align-items: center;
            justify-content: center;

            width: 25px;
            height: 25px;

            border-radius: 50%;
            background: #10233f;
            color: #ffffff;

            font-size: 0.65rem;
            font-weight: 850;
        }

        .ml-home-flow-title {
            margin-top: 0.75rem;
            color: #10233f;
            font-size: 0.9rem;
            font-weight: 850;
            line-height: 1.3;
        }

        .ml-home-flow-text {
            margin-top: 0.35rem;
            color: #5b6c80;
            font-size: 0.75rem;
            line-height: 1.45;
        }

        /* Explanation cards */

        .ml-home-concept-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1rem;
        }

        .ml-home-concept-card {
            padding: 1.05rem 1.1rem;

            border: 1px solid #d8e1ea;
            border-radius: 11px;
            background: #ffffff;
        }

        .ml-home-concept-title {
            color: #10233f;
            font-size: 0.92rem;
            font-weight: 850;
        }

        .ml-home-concept-text {
            margin-top: 0.35rem;
            color: #52647b;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        /* Start cards */

        .ml-home-start-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1rem;
        }

        .ml-home-start-card {
            display: flex;
            flex-direction: column;
            min-height: 190px;
            padding: 1.1rem;

            border: 1px solid #d8e1ea;
            border-radius: 11px;
            background: #ffffff;

            text-decoration: none !important;
            transition:
                transform 120ms ease,
                border-color 120ms ease,
                box-shadow 120ms ease;
        }

        .ml-home-start-card:hover {
            transform: translateY(-2px);
            border-color: #aebfce;
            box-shadow: 0 7px 20px rgba(15, 35, 63, 0.07);
        }

        .ml-home-start-kicker {
            color: #68788d;
            font-size: 0.66rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-home-start-title {
            margin-top: 0.45rem;
            color: #10233f;
            font-size: 1rem;
            font-weight: 900;
        }

        .ml-home-start-text {
            flex: 1;
            margin-top: 0.5rem;
            color: #52647b;
            font-size: 0.8rem;
            line-height: 1.5;
        }

        .ml-home-start-link {
            margin-top: 0.8rem;
            color: #285783;
            font-size: 0.78rem;
            font-weight: 850;
        }

        /* Main CTA */

        .ml-home-cta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1.5rem;

            margin-top: 2.2rem;
            padding: 1.25rem 1.35rem;

            border-radius: 12px;
            background: #10233f;
        }

        .ml-home-cta-title {
            color: #ffffff;
            font-size: 1.05rem;
            font-weight: 850;
        }

        .ml-home-cta-text {
            margin-top: 0.25rem;
            color: #bdcada;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        .ml-home-cta-link {
            flex: 0 0 auto;
            padding: 0.7rem 0.95rem;

            border-radius: 8px;
            background: #ffffff;
            color: #10233f !important;

            font-size: 0.8rem;
            font-weight: 850;
            text-decoration: none !important;
        }

        /* Disclaimer */

        .ml-home-disclaimer {
            margin-top: 1.2rem;
            color: #758397;
            font-size: 0.72rem;
            line-height: 1.5;
            text-align: center;
        }

        @media (max-width: 1050px) {
            .ml-home-flow {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .ml-home-start-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 700px) {
            .ml-home-title {
                font-size: 2rem;
            }

            .ml-home-flow,
            .ml-home-concept-grid,
            .ml-home-start-grid {
                grid-template-columns: 1fr;
            }

            .ml-home-flow-step,
            .ml-home-start-card {
                min-height: auto;
            }

            .ml-home-cta {
                align-items: stretch;
                flex-direction: column;
            }

            .ml-home-cta-link {
                text-align: center;
            }
        }
        /* =========================================================
           HOME — TEXT CONTRAST
           ========================================================= */

        /* Main explanatory/body text */
        .ml-home-description,
        .ml-home-positioning,
        .ml-home-section-description,
        .ml-home-flow-text,
        .ml-home-concept-text,
        .ml-home-start-text,
        .ml-home-cta-text {
            color: #1f2937;
        }

        /* Keep primary headings/titles navy */
        .ml-home-title,
        .ml-home-section-title,
        .ml-home-flow-title,
        .ml-home-concept-title,
        .ml-home-start-title,
        .ml-home-cta-title {
            color: #10233f;
        }

        /* Keep links blue */
        .ml-home-start-link {
            color: #285783;
        }

        /* Keep small supporting labels muted */
        .ml-home-eyebrow,
        .ml-home-start-kicker,
        .ml-home-disclaimer {
            color: #758397;
        }
        .ml-home-cta .ml-home-cta-title {
            color: #ffffff !important;
        }

        .ml-home-cta .ml-home-cta-text {
            color: #d7e0eb !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_home_page() -> None:
    _inject_home_css()

    st.html(
        """
        <main class="ml-home">
            <section class="ml-home-hero">
                <div class="ml-home-eyebrow">
                    MacroLens Research
                </div>

                <h1 class="ml-home-title">
                    How MacroLens Works
                </h1>

                <p class="ml-home-description">
                    MacroLens turns economic data into structured views of economies and financial
                    markets, helping you understand what is changing, why it matters and what it could mean for markets.
                </p>

                <div class="ml-home-positioning">
                    <strong>
                        MacroLens is a research tool, not a trading signal service. It organizes
                        macroeconomic, historical and market evidence to support your own analysis and
                        decisions.
                    </strong>
                </div>
            </section>

            <section class="ml-home-section">
                <div class="ml-home-section-header">
                    <div class="ml-home-section-title">
                        From economic data to research ideas
                    </div>

                    <div class="ml-home-section-description">
                        MacroLens follows a consistent research process. Economic indicators are organized
                        into macro environments, compared with history and then connected to financial
                        market behaviour and asset level research ideas.
                    </div>
                </div>

                <div class="ml-home-flow">
                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">1</div>

                        <div class="ml-home-flow-title">
                            Economic Data
                        </div>

                        <div class="ml-home-flow-text">
                            Economic indicators are collected across the
                            tracked economies.
                        </div>
                    </article>

                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">2</div>

                        <div class="ml-home-flow-title">
                            Five Macro Pillars
                        </div>

                        <div class="ml-home-flow-text">
                            Indicators are organized into Growth,
                            Inflation, Labour, Liquidity and Policy.
                        </div>
                    </article>

                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">3</div>

                        <div class="ml-home-flow-title">
                            Macro Environment
                        </div>

                        <div class="ml-home-flow-text">
                            The pillars combine to classify the current
                            economic environment and its direction.
                        </div>
                    </article>

                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">4</div>

                        <div class="ml-home-flow-title">
                            Historical Context
                        </div>

                        <div class="ml-home-flow-text">
                            Current conditions are compared with similar
                            historical environments.
                        </div>
                    </article>

                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">5</div>

                        <div class="ml-home-flow-title">
                            Market Analysis
                        </div>

                        <div class="ml-home-flow-text">
                            Macro evidence is compared with price trends,
                            momentum and market behaviour.
                        </div>
                    </article>

                    <article class="ml-home-flow-step">
                        <div class="ml-home-flow-number">6</div>

                        <div class="ml-home-flow-title">
                            Research Ideas
                        </div>

                        <div class="ml-home-flow-text">
                            Assets with meaningful changes or unresolved
                            evidence are surfaced for further review.
                        </div>
                    </article>
                </div>
            </section>

            <section class="ml-home-section">
                <div class="ml-home-section-header">
                    <div class="ml-home-section-title">
                        How to interpret the model
                    </div>

                    <div class="ml-home-section-description">
                        These three concepts appear throughout MacroLens
                        and help describe the quality and strength of the
                        model evidence.
                    </div>
                </div>

                <div class="ml-home-concept-grid">
                    <article class="ml-home-concept-card">
                        <div class="ml-home-concept-title">
                            Confidence
                        </div>

                        <div class="ml-home-concept-text">
                            Classification agreement and data coverage, not a calibrated probability of future market direction. A high reading means there is
                            enough underlying data and the indicators broadly agree on what environment we are in.     
                        </div>
                    </article>

                    <article class="ml-home-concept-card">
                        <div class="ml-home-concept-title">
                            Conviction
                        </div>

                        <div class="ml-home-concept-text">
                            How strong the current signal is. High conviction means the macro conditions point
                            strongly in one direction; low conviction means the environment may be identified
                            confidently, but the underlying signals are not especially strong.
                        </div>
                    </article>

                    <article class="ml-home-concept-card">
                        <div class="ml-home-concept-title">
                            System Stance
                        </div>

                        <div class="ml-home-concept-text">
                            The current research status after combining macro, market and historical evidence. It
                            indicates whether an asset is ready for review, should be watched or requires further
                            investigation.
                        </div>
                    </article>
                </div>
            </section>

            <section class="ml-home-section">
                <div class="ml-home-section-header">
                    <div class="ml-home-section-title">
                        Where should you start?
                    </div>

                    <div class="ml-home-section-description">
                        Each part of MacroLens answers a different
                        research question.
                    </div>
                </div>

                <div class="ml-home-start-grid">
                    <a
                        class="ml-home-start-card"
                        href="?page=MacroEngineGlobal"
                        target="_self"
                    >
                        <div class="ml-home-start-kicker">
                            Global context
                        </div>

                        <div class="ml-home-start-title">
                            Global Macro Monitor
                        </div>

                        <div class="ml-home-start-text">
                            Compare the four tracked economies and
                            identify where growth, inflation, liquidity
                            and policy conditions are diverging.
                        </div>

                        <div class="ml-home-start-link">
                            Compare economies →
                        </div>
                    </a>

                    <a
                        class="ml-home-start-card"
                        href="?page=ActiveIdeas"
                        target="_self"
                    >
                        <div class="ml-home-start-kicker">
                            What changed?
                        </div>

                        <div class="ml-home-start-title">
                            Active Ideas
                        </div>

                        <div class="ml-home-start-text">
                            See which monitored markets have experienced
                            meaningful changes and deserve further
                            attention.
                        </div>

                        <div class="ml-home-start-link">
                            Review changes →
                        </div>
                    </a>

                    <a
                        class="ml-home-start-card"
                        href="?page=ResearchWorkspace"
                        target="_self"
                    >
                        <div class="ml-home-start-kicker">
                            Asset research
                        </div>

                        <div class="ml-home-start-title">
                            Research Workspace
                        </div>

                        <div class="ml-home-start-text">
                            Investigate the macro thesis, market
                            confirmation and historical evidence behind
                            an individual asset view.
                        </div>

                        <div class="ml-home-start-link">
                            Explore an asset →
                        </div>
                    </a>

                    <a
                        class="ml-home-start-card"
                        href="?page=HistoricalRegimeExplorer"
                        target="_self"
                    >
                        <div class="ml-home-start-kicker">
                            Historical evidence
                        </div>

                        <div class="ml-home-start-title">
                            Regime Explorer
                        </div>

                        <div class="ml-home-start-text">
                            Study how major assets performed after
                            comparable macro environments appeared
                            historically.
                        </div>

                        <div class="ml-home-start-link">
                            Explore history →
                        </div>
                    </a>
                </div>
            </section>

            <section class="ml-home-cta">
                <div>
                    <div class="ml-home-cta-title">
                        Ready to explore the current macro environment?
                    </div>

                    <div class="ml-home-cta-text">
                        Compare current conditions across the United
                        States, Euro Area, United Kingdom and Japan.
                    </div>
                </div>

                <a
                    class="ml-home-cta-link"
                    href="?page=MacroEngineGlobal"
                    target="_self"
                >
                    Open Global Macro Monitor →
                </a>
            </section>

            <div class="ml-home-disclaimer">
                MacroLens model outputs are provided for research and educational purposes and
                are not financial advice or investment recommendations.
            </div>
        </main>
        """
    )