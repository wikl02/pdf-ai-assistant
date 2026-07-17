import os


def get_secret_value(name):
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st

        return st.secrets[name]
    except Exception:
        return None
