"""CSS leve para deixar o visual mais clean (pedido no layout)."""

APP_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #f4f7fb 0%, #eef2f7 100%);
    }
    .block-container {
        padding-top: 1.2rem;
        max-width: 1400px;
    }
    .orc-card {
        background: #ffffff;
        border: 1px solid #d9e2ec;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(31, 59, 91, 0.06);
        margin-bottom: 0.8rem;
    }
    .orc-title {
        font-family: "Segoe UI", "Helvetica Neue", sans-serif;
        color: #1f3b5b;
        font-weight: 700;
        font-size: 1.5rem;
        margin: 0 0 0.3rem 0;
    }
    .orc-sub {
        color: #627d98;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }
    .menu-btn button {
        height: 3.2rem;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    .proposta-box {
        background: #fff;
        border: 1px solid #d9e2ec;
        border-radius: 14px;
        padding: 1rem;
        min-height: 70vh;
    }
    .kpi {
        background: #f0f4f8;
        border-radius: 10px;
        padding: 0.7rem 0.8rem;
        border: 1px solid #d9e2ec;
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.4rem 0.6rem;
    }
</style>
"""
