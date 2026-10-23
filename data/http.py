"""Bounded, verified HTTP for provider files before handing bytes to pandas."""
from io import BytesIO

import pandas as pd
import requests


def download(url):
    response = requests.get(url, timeout=(10, 60))
    response.raise_for_status()
    return BytesIO(response.content)


def read_csv(url, **kwargs):
    return pd.read_csv(download(url), **kwargs)


def read_excel(url, **kwargs):
    return pd.read_excel(download(url), **kwargs)
