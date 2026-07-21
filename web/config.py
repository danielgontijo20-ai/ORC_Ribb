"""Configuração da aplicação web."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

SECRET_KEY = os.getenv("ORC_SECRET_KEY", "altere-esta-chave-em-producao-ribbontech")
SESSION_COOKIE = "orc_ribb_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12h

APP_NAME = "ORC_Ribb"
APP_ENV = os.getenv("ORC_ENV", "development")
