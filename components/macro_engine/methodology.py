import streamlit as st


def render_methodology_explainer() -> None:
    """
    Explain the Macro Engine in accessible language.

    This is static product documentation. It explains the engine's
    architecture without producing investment conclusions.
    """
    with st.expander(
        "What is the Macro Engine and how should I read it?",
        expanded=False,
    ):
        st.markdown(
            """
            The Macro Engine is a rules-based system that organizes
            economic data into a consistent assessment of the current
            macroeconomic environment.

            It does not predict asset prices or make investment
            recommendations. Its purpose is to summarize what the
            available economic evidence is currently indicating.
            """
        )

        st.markdown("### How the calculation works")

        st.markdown(
            """
            **1. Economic indicators**

            The engine begins with individual data series such as
            consumption, employment, inflation, housing, interest rates
            and financial conditions.

            Each indicator is evaluated using:

            - its current level relative to its own history;
            - whether its recent trend is improving or deteriorating;
            - the amount and quality of data available;
            - the freshness and consistency of the observations.
            """
        )

        st.markdown(
            """
            **2. Economic buckets**

            Related indicators are grouped into economic themes.

            For example, the Growth pillar includes buckets covering
            household demand, employment momentum, industrial activity
            and housing.
            """
        )

        st.markdown(
            """
            **3. Macro pillars**

            Bucket results are combined into five broad pillars:

            - Growth
            - Inflation
            - Labor
            - Liquidity
            - Policy

            Each pillar receives a current-state classification, a trend,
            breadth and confidence assessment.
            """
        )

        st.markdown(
            """
            **4. Macro environment**

            The Environment Engine combines the pillar results into three
            major dimensions:

            - activity impulse;
            - inflation impulse;
            - financial impulse.

            Their combination determines the current macro-environment
            classification.
            """
        )

        st.markdown(
            """
            **5. Confidence and conviction**

            Confidence reflects the quality, completeness and consistency
            of the underlying data.

            Conviction reflects how clearly the current scores fit within
            the assigned environment. A low-conviction result can occur
            when the economy is close to a classification boundary or when
            different parts of the model disagree.
            """
        )

        st.info(
            "The Macro Engine is an evidence-organizing framework. "
            "Investment interpretation belongs in the Research section."
        )