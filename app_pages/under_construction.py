import streamlit as st


def render_under_construction_page(page_name):

    st.markdown("#")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:

        st.markdown(
            "<h4 style='text-align:center;color:#64748b;'>Research Page</h4>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<h1 style='text-align:center;'>{page_name}</h1>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<h3 style='text-align:center;color:#334155;'>Under Development</h3>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <p style='text-align:center;color:#64748b;font-size:18px;'>
            This page is currently being developed as part of the MacroLens platform.
            <br><br>
            Model signals, analyst interpretation, and market implications
            will be added over time.
            </p>
            """,
            unsafe_allow_html=True,
        )