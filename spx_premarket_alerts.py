import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import datetime
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import csv
import openai
import pytz

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
finnhub_api_key = os.getenv("FINNHUB_API_KEY")
marketaux_api_key = os.getenv("MARKETAUX_API_KEY")
openai_model = "gpt-3.5-turbo"




# =============================
# 📋 Utility Functions
# =============================

import json

def classify_headlines_openai_bulk(headlines, batch_size=10):
    score_map = {"📈": 3, "📉": -3, "🔹": 0}
    all_classified = []

    for i in range(0, len(headlines), batch_size):
        chunk = headlines[i:i+batch_size]
        try:
            prompt = [
                {"role": "system", "content": (
                    "You are a financial sentiment classifier.\n\n"
                    "Classify each headline as:\n"
                    "📈 (bullish), 📉 (bearish), or 🔹 (neutral), with confidence (0.0–1.0) and a brief reason.\n"
                    "Respond ONLY with a JSON list like:\n"
                    "[{\"sentiment\": \"📈\", \"confidence\": 0.8, \"reason\": \"Rate cuts expected\"}, ...]"
                )},
                {"role": "user", "content": "\n".join(chunk)}
            ]

            response = openai.chat.completions.create(
                model=openai_model,
                messages=prompt,
                temperature=0.3,
                max_tokens=700
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.strip("```json").strip("```").strip()

            try:
                parsed = json.loads(result_text)
            except json.JSONDecodeError:
                last_valid = result_text.rfind("}")
                result_text = result_text[:last_valid+1] + "]"
                parsed = json.loads(result_text)

            for item in parsed:
                emoji = item.get("sentiment", "🔹")
                score = score_map.get(emoji, 0)
                reason = item.get("reason", "")
                conf = float(item.get("confidence", 0))
                all_classified.append((emoji, score, reason, conf))

        except Exception as e:
            print("❌ GPT classification failed:", e)
            all_classified.extend([("🔹", 0, "Error", 0)] * len(chunk))

    return all_classified

    
def is_market_relevant(text):
    keywords = [
        "fed", "federal reserve", "interest rate", "tariff", "rate", "inflation", "disinflation",
        "deflation", "yields", "bond", "treasury", "quantitative tightening", "quantitative easing",
        "hawkish", "dovish", "fomc", "central bank", "earnings", "revenue", "guidance",
        "stocks", "markets", "indices", "s&p", "nasdaq", "dow", "volatility", "vix",
        "recession", "soft landing", "jobless", "unemployment", "nonfarm", "cpi", "ppi", "gdp",
        "retail sales", "housing", "consumer sentiment", "ism", "pce", "commodities", "oil prices",
        "energy prices", "geopolitical", "china", "opec", "rate hike", "rate cut", "ecb", "boe", "boj",
        "debt ceiling", "fiscal policy", "economic outlook", "layoffs", "banking crisis", "credit rating",
        "supply chain", "default", "liquidity", "volumes", "short selling", "options expiry", "earnings call"
    ]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)

# =============================
# 📋 News Scrapers
# =============================

def scrape_headlines(url, selector, base_url=""):
    headlines = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        for el in soup.select(selector)[:10]:
            text = el.get_text(strip=True)
            link = el.get("href", "")
            if text and is_market_relevant(text):
                full_link = f"{base_url}{link}" if link.startswith("/") else link
                headlines.append(f"{text} - {full_link}")
    except Exception as e:
        print(f"⚠️ Error scraping {url}:", e)
    return headlines
'''
def fetch_finnhub_news():
    headlines = []
    url = f"https://finnhub.io/api/v1/news?category=general&token={finnhub_api_key}"
    try:
        response = requests.get(url).json()
        for item in response[:10]:
            title = item.get("headline", "")
            url = item.get("url", "")
            if title:
                headlines.append(f"{title} - {url}")
    except Exception as e:
        print("❌ Finnhub news fetch failed:", e)
    return headlines

def fetch_marketaux_news():
    headlines = []
    published_after = (datetime.datetime.now(datetime.timezone.utc) - timedelta(hours=3)).isoformat()
    url = f"https://api.marketaux.com/v1/news/all?symbols=SPY&published_after={published_after}&filter_entities=true&language=en&api_token={marketaux_api_key}"
    try:
        response = requests.get(url).json()
        for article in response.get("data", [])[:10]:
            title = article.get("title", "")
            url = article.get("url", "")
            if title:
                headlines.append(f"{title} - {url}")
    except Exception as e:
        print("❌ Marketaux news fetch failed:", e)
    return headlines
'''
def fetch_investing_news():
    headlines = []
    try:
        url = "https://www.investing.com/news/stock-market-news"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        for el in soup.select("div.textDiv a.title")[:10]:
            title = el.get_text(strip=True)
            link = "https://www.investing.com" + el.get("href", "")
            if title:
                headlines.append(f"{title} - {link}")
    except Exception as e:
        print("❌ Investing.com news fetch failed:", e)
    return headlines

def fetch_yahoo_finance_news():
    headlines = []
    try:
        url = "https://finance.yahoo.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        for el in soup.select('h3 a')[:10]:
            title = el.get_text(strip=True)
            link = el.get("href", "")
            full_link = f"https://finance.yahoo.com{link}" if link.startswith("/") else link
            if title and is_market_relevant(title):
                headlines.append(f"{title} - {full_link}")
    except Exception as e:
        print("❌ Yahoo Finance news fetch failed:", e)
    return headlines

def fetch_bloomberg_headlines():
    headlines = []
    try:
        url = "https://www.bloomberg.com/markets"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.select("a.story-package-module__story__headline-link")[:10]:
            title = tag.get_text(strip=True)
            link = tag.get("href")
            if link and not link.startswith("http"):
                link = "https://www.bloomberg.com" + link
            if title and is_market_relevant(title):
                headlines.append(f"{title} - {link}")
    except Exception as e:
        print("❌ Bloomberg news fetch failed:", e)
    return headlines
def get_all_market_news():
    headlines_raw = []

    # 📺 CNBC
    headlines_raw += scrape_headlines("https://www.cnbc.com/world/?region=world", "a.Card-title")

    # 🌍 Other Sources
    #headlines_raw += fetch_finnhub_news()
    #headlines_raw += fetch_marketaux_news()
    headlines_raw += fetch_investing_news()
    headlines_raw += fetch_yahoo_finance_news()
    headlines_raw += fetch_bloomberg_headlines()

    
   # Deduplicate and filter for relevance
    headlines_raw = list(set([h for h in headlines_raw if is_market_relevant(h)]))


    # 🧠 Classify with OpenAI
    classified = classify_headlines_openai_bulk(headlines_raw)

    # 🧩 Final structure
    enhanced_news = []
    for original, sentiment in zip(headlines_raw, classified):
        emoji, score, reason, confidence = sentiment
        enhanced_news.append((emoji, score, f"{emoji} {original} — {reason}", confidence))

    print("Total headlines collected:", len(headlines_raw))
    print("\nSample headlines:")
    for h in headlines_raw[:3]:
        print(h)

    return enhanced_news



# =============================
# 📋 Market Data
# =============================

def get_price_from_investing(url):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--log-level=3")  # Suppress USB/logging warnings
        options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Optional extra suppressor

        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(4)
        price = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]').text.replace(",", "")
        driver.quit()
        return float(price)
    except Exception as e:
        print(f"⚠️ Error retrieving price from {url}:", e)
        return "N/A"

def get_spx():
    return get_price_from_investing("https://www.investing.com/indices/us-spx-500")

def get_vix():
    return get_price_from_investing("https://www.investing.com/indices/volatility-s-p-500")

def get_es():
    return get_price_from_investing("https://www.investing.com/indices/us-spx-500-futures")

# =============================
# 📋 Analysis & Bias
# =============================

def estimate_direction(spx, es, prev_es, sentiment_score, vix, news):
    score = 0
    reasons = []

    # Pillar 1: ES Gap (Price Action)
    if isinstance(es, float) and isinstance(prev_es, float):
        gap = es - prev_es
        reasons.append(f"ES Gap: {gap:+.2f} pts")
        if gap > 8:
            score += 1
            reasons.append("✅ Bullish: Strong overnight futures gap")
        elif gap < -8:
            score -= 1
            reasons.append("❌ Bearish: Weak overnight futures gap")
    else:
        reasons.append("⚠️ Gap calculation skipped (Missing ES data)")

    # Pillar 2: AI Sentiment (News Context)
    avg_conf = sum(c for _, _, _, c in news) / len(news) if news else 0
    reasons.append(f"AI Sentiment Score: {sentiment_score} (Conf: {round(avg_conf, 2)})")
    
    if sentiment_score >= 3:
        score += 1
        reasons.append("✅ Bullish: News sentiment is positive")
    elif sentiment_score <= -3:
        score -= 1
        reasons.append("❌ Bearish: News sentiment is negative")

    # Pillar 3: VIX (Volatility/Fear)
    if isinstance(vix, float):
        if vix > 25:
            score -= 1
            reasons.append(f"❌ Bearish: High VIX ({vix}) suggests elevated risk")
        elif vix < 15:
            score += 1
            reasons.append(f"✅ Bullish: Low VIX ({vix}) suggests market calm")

    # Final Decision (Forced Binary)
    if score > 0 or (score == 0 and sentiment_score > 0):
        direction = "📈 Forced Bullish"
    else:
        direction = "📉 Forced Bearish"

    return direction, reasons

# =============================
# 📅 Logging
# =============================

def log_premarket_prediction(date, spx, es, vix, sentiment_score, direction, news):
    log_file = "market_predictions.csv"
    file_exists = os.path.isfile(log_file)

    news_str = " | ".join([h for _, _, h, _ in news])



    with open(log_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "date", "spx", "es", "vix", "sentiment_score",
                "predicted_trend", "actual_trend", "actual_spx_close", "Match/Miss", "news"
            ])
        writer.writerow([
            date, spx, es, vix, sentiment_score,
            direction, "nan", "nan", "nan", news_str
        ])

# =============================
# ⏰ Time Control & Scheduler
# =============================

def now_chicago():
    tz = pytz.timezone("America/Chicago")
    return datetime.datetime.now(tz)

def wait_until_chicago(target_h, target_m, max_wait_minutes=60):
    """Wait until the clock hits the exact target time in Chicago."""
    start = now_chicago()
    deadline = start + timedelta(minutes=max_wait_minutes)

    while True:
        now = now_chicago()
        target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)

        # If we reached or passed the target, stop waiting
        if now >= target:
            return

        # Safety timeout
        if now >= deadline:
            print(f"⚠️ Wait timeout reached. Proceeding at {now}")
            return

        time.sleep(10) # Check every 10 seconds

# =============================
# 📧 Email Notifier
# =============================

def send_email(subject, spx, vix, es, news, direction, reasons, move_msg, to_email):
    try:
        import pytz
        # Get current time in US/Eastern
        eastern = pytz.timezone('US/Eastern')
        current_time_est = datetime.datetime.now(eastern).strftime('%I:%M %p ET')

        message = MIMEMultipart("alternative")
        message["From"] = os.getenv("EMAIL_USER")
        message["To"] = to_email
        message["Subject"] = subject
        headline_lines = "\n".join([f"- {h}" for _, _, h, _ in news])
        reason_lines = "\n".join([f"- {r}" for r in reasons])
        # Plaintext fallback
        body_text = f"""
                
                📊 Pre-Market Alert for {datetime.date.today()}
                🔹 SPX: {spx}  🔺 VIX: {vix}  📉 ES: {es}

                📰 Headlines:
                {headline_lines}

                📊 Market Bias: {direction}
                {reason_lines}

                📉 Expected Move: {move_msg}
                Generated by CDUS Trading Bot • {current_time_est}
                """

        # HTML version
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #0d6efd;">📊 Pre-Market Alert for {datetime.date.today()}</h2>
            <p>
                <strong>🔹 SPX:</strong> {spx} &nbsp;&nbsp;
                <strong>🔺 VIX:</strong> {vix} &nbsp;&nbsp;
                <strong>📉 ES:</strong> {es}
            </p>

            <h3>📰 Headlines:</h3>
            <ul>
                {''.join(f"<li>{h}</li>" for _, _, h, _ in news)}
            </ul>

            <h3>📊 Market Bias: {direction}</h3>
                        
            <br>
            <p style="font-size: 0.9em; color: #888;">Generated by CDUS Trading Bot • {current_time_est}</p>
        </body>
        </html>
        """

        # Attach both parts
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(message)
            print("✅ Email sent.")
    except Exception as e:
        print("❌ Email failed:", e)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def fetch_finance_data(symbol):
    """Internal helper to get price and prev close from Google Finance"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.google.com/finance/quote/{symbol}"
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        price_el = soup.select_one("div.YMlKec.fxKbKc")
        current_price = float(price_el.text.replace(",", "").replace("$", "")) if price_el else None
        
        prev_close = None
        for row in soup.select("div.gyFHrc"):
            if "Previous close" in row.text:
                val_text = row.select_one("div.P6K39c").text
                prev_close = float(val_text.replace(",", "").replace("$", ""))
                break
        return current_price, prev_close
    except Exception:
        return None, None
# =============================
# 📊 Main
# =============================

def main():
    now = now_chicago()
    print(f"Current Chicago Time: {now.strftime('%I:%M %p %Z')}")

    # Slot Identification
    if now.hour < 10:
        target_h, target_m, slot_label = 8, 0, "8:30 Trade Signal"
    elif 10 <= now.hour < 13:
        target_h, target_m, slot_label = 11, 30, "12:00 Trade Signal"
    else:
        print("❌ Outside scheduled window. Exiting.")
        return

    print(f"⏳ Waiting for {target_h}:{target_m:02d} AM Sharp...")
    wait_until_chicago(target_h, target_m)

    # 1. Data Collection
    spx = get_spx()
    vix = get_vix()
    es = get_es()
    
    # IMPORTANT: Ensure you have fetch_finance_data defined to get prev_es
    # Using the S&P 500 Index for a reliable previous close comparison
    _, prev_es = fetch_finance_data(".INX:INDEXSP") 

    # 2. AI News Analysis
    news = get_all_market_news()
    sentiment_score = sum(score for _, score, _, _ in news)

    # 3. Merged Bias Logic
    direction, reasons = estimate_direction(spx, es, prev_es, sentiment_score, vix, news)

    # 4. SET THE NEW SUBJECT LINE HERE
    subject = f"CDUS Precision Signal: {direction} | {slot_label}"

    # 5. Final Alert
    send_email(
        subject=subject,
        spx=spx,
        vix=vix,
        es=es,
        news=news,
        direction=direction,
        reasons=reasons,
        move_msg="N/A",
        to_email=os.getenv("EMAIL_TO")
    )
    print(f"✅ {slot_label} Sent Successfully with Precision Logic.")


if __name__ == "__main__":
    main()
