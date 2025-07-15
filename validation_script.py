import pandas as pd
import datetime
import pytz
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ---------- Fetch SPX Close from Investing.com ----------
def get_spx_close():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        driver = webdriver.Chrome(options=options)
        driver.get("https://www.investing.com/indices/us-spx-500")
        time.sleep(4)
        price = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]').text.replace(",", "")
        driver.quit()
        return float(price)
    except Exception as e:
        print("Error fetching SPX close:", e)
        return None

# ---------- Evaluate and Update Prediction Logs ----------
def evaluate_predictions(log_file="market_predictions.csv"):
    try:
        df = pd.read_csv(
            log_file,
            parse_dates=['date'],
            quoting=1,
            quotechar='"',
            escapechar='\\',
            encoding='utf-8',
            on_bad_lines='warn'
        )
    except Exception as e:
        print("❌ Error reading CSV file:", e)
        return

    # Fill missing columns if absent
    for col in ['actual_spx_close', 'actual_trend', 'Match/Miss']:
        if col not in df.columns:
            df[col] = "N/A"

    # Get today's CST date
    now_cst = datetime.datetime.now(pytz.timezone("US/Central")).date()
    print(f"📅 Today CST: {now_cst}")

    # Normalize 'date' column for comparison
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

    # Clean and standardize actual_trend column
    df['actual_trend'] = df['actual_trend'].astype(str).str.strip().str.lower()

    # Identify rows missing actuals
    mask = (
        (df['date'] == now_cst) &
        (df['actual_trend'].isin(["n/a", "nan", "", "na"]))
    )

    if mask.sum() == 0:
        print("✅ No missing actuals for today.")
        return

    print(f"🟡 Found {mask.sum()} entries missing actuals. Proceeding to update...")

    # Fetch actual SPX close
    actual_close = get_spx_close()
    if actual_close is None:
        print("❌ Failed to fetch SPX close.")
        return

    # Apply updates
    for idx in df[mask].index:
        predicted = df.loc[idx, 'predicted_trend']
        spx_open = df.loc[idx, 'spx']

        try:
            spx_open = float(spx_open)
            actual_trend = "Bullish" if actual_close > spx_open else "Bearish"
            match = "1" if actual_trend.lower() in predicted.lower() else "0"
        except Exception as e:
            print(f"⚠️ Error processing row {idx}: {e}")
            actual_trend, match = "n/a", "n/a"

        df.at[idx, 'actual_spx_close'] = str(actual_close)
        df.at[idx, 'actual_trend'] = actual_trend
        df.at[idx, 'Match/Miss'] = match

    df.to_csv(log_file, index=False)
    print(f"✅ Updated {mask.sum()} entries with actual close: {actual_close}")

# Run
if __name__ == "__main__":
    evaluate_predictions()
