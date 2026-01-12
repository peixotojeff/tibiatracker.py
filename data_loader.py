# data_loader.py
import os
import json
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

logger = logging.getLogger(__name__)

def load_google_credentials() -> Credentials:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        try:
            info = json.loads(creds_json)
        except json.JSONDecodeError:
            s = creds_json.strip().strip('"').replace("\\n", "\n")
            info = json.loads(s)
        return Credentials.from_service_account_info(info, scopes=scopes)
    elif os.path.exists("credenciais.json"):
        return Credentials.from_service_account_file("credenciais.json", scopes=scopes)
    else:
        raise ValueError("Defina GOOGLE_CREDENTIALS ou forneça credenciais.json")


def load_sheet_data() -> pd.DataFrame:
    """Carrega e pré-processa dados da planilha do Google Sheets."""
    creds = load_google_credentials()
    client = gspread.authorize(creds)

    sheet_id = os.getenv("GOOGLE_SPREADSHEET_ID") or "1sFde6uvz0UdR1Vd1KJ7kflxqZd_-ydJuphesMMOLyMA"
    worksheet_name = os.getenv("GOOGLE_WORKSHEET_NAME", "EXP/DIA")

    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)

    df["create_at"] = pd.to_datetime(df["create_at"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["create_at", "Experience"]).sort_values("create_at")
    df["Experience"] = pd.to_numeric(df["Experience"], errors="coerce")
    df["daily_exp"] = df["Experience"].diff().fillna(0).clip(lower=0)

    logger.info(f"Dados carregados: {len(df)} registros")
    return df