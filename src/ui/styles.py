"""Tema visual do ORC_Ribb — contraste reforçado, layout estável nas colunas."""

APP_CSS = """
<style>
    :root {
        --orc-primary: #0A3358;
        --orc-primary-2: #145A8A;
        --orc-accent: #178F7C;
        --orc-accent-soft: #D2F1EB;
        --orc-bg-1: #EAF1F6;
        --orc-bg-2: #DDE7EF;
        --orc-border: #9FB4C7;
        --orc-border-strong: #6F8AA3;
        --orc-text: #10283D;
        --orc-muted: #4E667A;
        --orc-active-glow: rgba(31, 158, 138, 0.35);
    }

    header[data-testid="stHeader"] {
        background: transparent;
        height: 0rem;
    }
    div[data-testid="stToolbar"] { display: none; }

    .stApp {
        background: linear-gradient(165deg, var(--orc-bg-1) 0%, var(--orc-bg-2) 55%, #d5e2ec 100%);
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
    .orc-title {
        font-family: "Segoe UI", "Helvetica Neue", sans-serif;
        font-weight: 750;
        font-size: 1.55rem;
        margin: 0 0 0.25rem 0;
    }
    .orc-sub { color: var(--orc-muted); font-size: 0.95rem; margin-bottom: 1rem; }
    .orc-top-spacer { height: 0.35rem; }

    /* Cards Streamlit — sem sticky/transform (quebravam alinhamento da prévia) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%) !important;
        border: 2px solid var(--orc-border-strong) !important;
        border-radius: 14px !important;
        box-shadow: 0 12px 30px rgba(10, 51, 88, 0.10) !important;
        padding: 0.35rem 0.2rem !important;
        margin-bottom: 0.75rem !important;
        animation: orcFade 0.3s ease-out;
    }

    @keyframes orcFade {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, var(--orc-accent-soft) 140%);
        border: 2px solid var(--orc-border);
        border-radius: 12px;
        padding: 0.45rem 0.65rem;
    }
    div[data-testid="stMetric"] label { color: var(--orc-muted) !important; }

    .stButton > button {
        border-radius: 11px !important;
        border: 2px solid var(--orc-border) !important;
        font-weight: 650 !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stButton > button:hover {
        border-color: var(--orc-accent) !important;
        box-shadow: 0 6px 16px rgba(10, 51, 88, 0.12);
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, var(--orc-primary) 0%, var(--orc-primary-2) 100%) !important;
        border: 2px solid var(--orc-primary) !important;
        color: white !important;
        box-shadow: 0 6px 18px rgba(10, 51, 88, 0.22), 0 0 0 3px var(--orc-active-glow);
    }

    .stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label {
        color: var(--orc-text) !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="select"] > div,
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border: 2px solid var(--orc-border-strong) !important;
        background: #fbfdff !important;
        color: var(--orc-text) !important;
    }
    div[data-baseweb="select"] > div:focus-within,
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--orc-accent) !important;
        box-shadow: 0 0 0 3px var(--orc-active-glow) !important;
    }

    .stSuccess { border-left: 5px solid var(--orc-accent); }
    .orc-total-bar {
        background: linear-gradient(135deg, var(--orc-primary) 0%, var(--orc-accent) 120%);
        color: #fff;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin: 0.7rem 0 1rem 0;
        font-weight: 700;
        box-shadow: 0 8px 20px rgba(10, 51, 88, 0.18);
    }
    .menu-btn button {
        height: 3.2rem;
        border-radius: 12px !important;
        font-weight: 650 !important;
    }
</style>
"""
