from __future__ import annotations

from html import escape

import streamlit as st


def inject_page_intro_css() -> None:
    st.markdown(
        """
        <style>
        .ml-page-intro {
            max-width: 1120px;
            margin: 18px auto 24px;
        }

        .ml-page-intro-eyebrow {
            color: #64748b;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .ml-page-intro-title {
            color: #0f172a;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.035em;
            line-height: 1.1;
        }

        .ml-page-intro-description {
            max-width: 850px;
            color: #5f6f83;
            font-size: 0.98rem;
            line-height: 1.6;
            margin-top: 0.55rem;
        }

        .ml-page-intro-guide {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            max-width: 850px;
            margin-top: 1rem;
            padding: 0.85rem 1rem;
            background: #f5f8fc;
            border: 1px solid #dbe4ef;
            border-left: 4px solid #2d5f9a;
            border-radius: 9px;
        }

        .ml-page-intro-guide-label {
            flex: 0 0 auto;
            color: #244f7f;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.045em;
            text-transform: uppercase;
            padding-top: 0.08rem;
        }

        .ml-page-intro-guide-text {
            color: #45566d;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        @media (max-width: 700px) {
            .ml-page-intro {
                margin-top: 10px;
            }

            .ml-page-intro-title {
                font-size: 1.65rem;
            }

            .ml-page-intro-guide {
                display: block;
            }

            .ml-page-intro-guide-label {
                margin-bottom: 0.3rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_intro(
    *,
    title: str,
    description: str,
    guide: str,
    eyebrow: str | None = None,
    max_width: int = 1120,
) -> None:
    inject_page_intro_css()

    eyebrow_html = (
        f"""
        <div class="ml-page-intro-eyebrow">
            {escape(eyebrow)}
        </div>
        """
        if eyebrow
        else ""
    )

    st.html(
        f"""
        <section
            class="ml-page-intro"
            style="max-width: {max_width}px;"
        >
            {eyebrow_html}

            <div class="ml-page-intro-title">
                {escape(title)}
            </div>

            <div class="ml-page-intro-description">
                {escape(description)}
            </div>

            <div class="ml-page-intro-guide">
                <div class="ml-page-intro-guide-label">
                    How to use this page
                </div>

                <div class="ml-page-intro-guide-text">
                    {escape(guide)}
                </div>
            </div>
        </section>
        """
    )