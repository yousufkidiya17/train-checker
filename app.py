import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import asyncio
from playwright.async_api import async_playwright
import re

st.set_page_config(
    page_title="Train Availability Checker",
    page_icon="🚂",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    .stButton>button {
        background-color: #ff6b35;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
    }
    .stButton>button:hover { background-color: #ff8c5a; }
</style>
""", unsafe_allow_html=True)


class TrainScraper:
    async def search_trains_async(self, from_station: str, to_station: str, date: str):
        url = f"https://www.confirmtkt.com/rbooking/trains/from/{from_station}/to/{to_station}/{date}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(15000)
            
            text = await page.evaluate("document.body.innerText")
            await browser.close()
            
            return self._parse_text(text, from_station, to_station, date)
    
    def _parse_text(self, text: str, source: str, destination: str, date: str):
        lines = text.split('\n')
        trains = []
        
        for line in lines:
            line = line.strip()
            train_match = re.match(r'(\d{5,6})\s*(.+?)(?:\s+(CNF|WL|Regret|N\/A))?\s*$', line)
            
            if train_match:
                train_num = train_match.group(1)
                train_name = train_match.group(2).strip()[:50]
                status_raw = train_match.group(3) if train_match.group(3) else ""
                
                if 'WL' in status_raw:
                    status = f"WL"
                elif 'CNF' in status_raw:
                    status = "Confirm"
                elif 'Regret' in status_raw:
                    status = "Regret"
                else:
                    status = "Check"
                
                trains.append({
                    "Train No": train_num,
                    "Train Name": train_name,
                    "Status": status
                })
        
        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains": trains[:15]
        }


POPULAR_STATIONS = {
    "NDLS": "New Delhi",
    "BSB": "Varanasi", 
    "CNB": "Kanpur",
    "MMCT": "Mumbai Central",
    "HWH": "Howrah",
    "CSTM": "Mumbai CST",
    "MAS": "Chennai Central",
    "SBC": "Bangalore City",
    "HYB": "Hyderabad",
    "JP": "Jaipur",
    "ADI": "Ahmedabad",
    "LDH": "Ludhiana"
}

async def search_trains_async(from_station, to_station, date):
    scraper = TrainScraper()
    return await scraper.search_trains_async(from_station, to_station, date)


st.title("🚂 Train Availability Checker")
st.markdown("Check Indian Railway seat availability easily!")

col1, col2, col3 = st.columns(3)

with col1:
    from_station = st.selectbox(
        "From Station",
        options=list(POPULAR_STATIONS.keys()),
        format_func=lambda x: f"{x} - {POPULAR_STATIONS[x]}",
        index=0
    )

with col2:
    to_station = st.selectbox(
        "To Station", 
        options=list(POPULAR_STATIONS.keys()),
        format_func=lambda x: f"{x} - {POPULAR_STATIONS[x]}",
        index=7
    )

with col3:
    default_date = datetime.now() + timedelta(days=7)
    travel_date = st.date_input(
        "Travel Date",
        value=default_date,
        min_value=datetime.now(),
        max_value=datetime.now() + timedelta(days=120)
    )

date_str = travel_date.strftime("%d-%m-%Y")

if st.button("🔍 Search Trains", use_container_width=True):
    with st.spinner("Loading trains... (may take 15-20 seconds)"):
        result = asyncio.run(search_trains_async(from_station, to_station, date_str))
        
        if result.get("trains"):
            st.success(f"Found {len(result['trains'])} trains!")
            
            df = pd.DataFrame(result["trains"])
            
            def color_status(val):
                if 'Confirm' in str(val):
                    return '✅ ' + str(val)
                elif 'WL' in str(val):
                    return '⏳ ' + str(val)
                elif 'Regret' in str(val):
                    return '❌ ' + str(val)
                return str(val)
            
            df['Status'] = df['Status'].apply(color_status)
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No trains found! Try different stations or date.")

st.markdown("---")
st.markdown("**Popular Routes:**")
route_cols = st.columns(4)
routes = [
    ("NDLS", "BSB", "New Delhi → Varanasi"),
    ("MMCT", "ADI", "Mumbai → Ahmedabad"),
    ("HWH", "NDLS", "Howrah → New Delhi"),
    ("MAS", "SBC", "Chennai → Bangalore")
]

for i, (frm, to, label) in enumerate(routes):
    with route_cols[i % 4]:
        st.button(label, key=f"route_{i}")

st.markdown("---")
st.caption("Data from ConfirmTkt.com | Use responsibly")
