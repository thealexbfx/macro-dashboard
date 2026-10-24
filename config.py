import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_secret(section: str, key: str, env_key: str | None = None) -> str | None:
    """Prefer Streamlit secrets, fall back to .env / environment variables."""
    env_key = env_key or key
    try:
        return st.secrets[section][key]
    except Exception:
        return os.getenv(env_key)

FRED_API_KEY = get_secret("fred", "api_key", "FRED_API_KEY")
ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")
OPENAI_API_KEY = get_secret("openai", "api_key", "OPENAI_API_KEY")
BLS_API_KEY = get_secret("openai", "BLS_API_KEY", "BLS_API_KEY")
BEA_API_KEY = get_secret("openai", "BEA_API_KEY", "BEA_API_KEY")
