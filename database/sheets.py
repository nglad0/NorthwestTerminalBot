# sheets.py

import gspread

from config import (
    GOOGLE_SHEET_ID,
    GOOGLE_WORKSHEET_NAME,
    GOOGLE_SERVICE_ACCOUNT_FILE,
)


def get_worksheet():
    """Connect to Google Sheets and return the configured worksheet."""

    client = gspread.service_account(
        filename=GOOGLE_SERVICE_ACCOUNT_FILE
    )

    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = spreadsheet.worksheet(GOOGLE_WORKSHEET_NAME)

    return worksheet