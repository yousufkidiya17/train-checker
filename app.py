import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import asyncio

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

async def search_trains_async(from_station: str, to_station: str, date: str):
    """Search trains using Playwright"""
    from playwright.async_api import async_playwright
    
    url = f"https://www.confirmtkt.com/rbooking/trains/from/{from_station}/to/{to_station}/{date}"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            await page.wait_for_timeout(3000)
            
            html = await page.content()
            await browser.close()
            
            return {
                "url": url,
                "html_length": len(html),
                "html": html[:5000]
            }
    except Exception as e:
        return {"error": str(e), "url": url}

def search_trains(from_station: str, to_station: str, date: str):
    """Sync wrapper for async function"""
    return asyncio.run(search_trains_async(from_station, to_station, date))


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
        index=1
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
    with st.spinner("Loading page with browser..."):
        result = search_trains(from_station, to_station, date_str)
        
        st.write("### Debug Info")
        st.write(f"**URL:** {result.get('url', 'N/A')}")
        st.write(f"**HTML Length:** {result.get('html_length', 'N/A')}")
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            with st.expander("View HTML Content"):
                st.text(result.get('html', 'No HTML'))
            
            st.info("Scraper ready! Install playwright: pip install playwright && playwright install chromium")

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
