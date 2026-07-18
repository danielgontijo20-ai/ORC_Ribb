"""Tema visual do ORC_Ribb — tons azul/teal industriais (harmonia com logos técnicas)."""

APP_CSS = """
<style>
    :root {
        --orc-primary: #0D3B66;
        --orc-primary-2: #145A8A;
        --orc-accent: #1F9E8A;
        --orc-accent-soft: #D8F3EF;
        --orc-bg-1: #F2F7F9;
        --orc-bg-2: #E7EEF3;
        --orc-card: #FFFFFF;
        --orc-border: #C9D7E3;
        --orc-text: #16324A;
        --orc-muted: #5B7388;
    }

    /* Evita topo cortado pelo header do Streamlit */
    header[data-testid="stHeader"] {
        background: transparent;
        height: 0rem;
    }
    div[data-testid="stToolbar"] {
        display: none;
    }
    .stApp {
        background: linear-gradient(165deg, var(--orc-bg-1) 0%, var(--orc-bg-2) 55%, #dfe9f0 100%);
        color: var(--orc-text);
    }
    .block-container {
        padding-top: 2.6rem !important;
        padding-bottom: 2.2rem !important;
        max-width: 1400px;
    }
    h1, h2, h3, h4, .orc-title {
        color: var(--orc-primary) !important;
    }
    .orc-card {
        background: var(--orc-card);
        border: 1px solid var(--orc-border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 28px rgba(13, 59, 102, 0.07);
        margin-bottom: 0.8rem;
    }
    .orc-title {
        font-family: "Segoe UI", "Helvetica Neue", sans-serif;
        color: var(--orc-primary);
        font-weight: 750;
        font-size: 1.55rem;
        margin: 0 0 0.25rem 0;
        letter-spacing: -0.01em;
    }
    .orc-sub {
        color: var(--orc-muted);
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }
    .menu-btn button {
        height: 3.2rem;
        border-radius: 12px !important;
        font-weight: 650 !important;
    }
    .proposta-box {
        background: var(--orc-card);
        border: 1px solid var(--orc-border);
        border-radius: 14px;
        padding: 1rem;
        min-height: 70vh;
        box-shadow: 0 10px 28px rgba(13, 59, 102, 0.06);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, var(--orc-accent-soft) 140%);
        border: 1px solid var(--orc-border);
        border-radius: 12px;
        padding: 0.45rem 0.65rem;
    }
    div[data-testid="stMetric"] label {
        color: var(--orc-muted) !important;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, var(--orc-primary) 0%, var(--orc-primary-2) 100%);
        border: none;
        color: white;
    }
    .stButton > button:hover {
        border-color: var(--orc-accent);
    }
    .stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label {
        color: var(--orc-text) !important;
        font-weight: 600;
    }
    div[data-baseweb="select"] > div,
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border-color: var(--orc-border) !important;
    }
    .stSuccess {
        border-left: 4px solid var(--orc-accent);
    }
    /* Espaço extra no topo das telas internas */
    .orc-top-spacer {
        height: 0.35rem;
    }
</style>
"""
