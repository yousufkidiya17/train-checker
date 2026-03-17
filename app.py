import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
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
    BASE_URL = "https://www.confirmtkt.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def search_trains(self, from_station: str, to_station: str, date: str):
        """Search trains between stations"""
        url = f"{self.BASE_URL}/rbooking/trains/from/{from_station}/to/{to_station}/{date}"
        
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}", "trains": [], "debug": f"URL: {url}"}
            
            result = self._parse_trains(response.text, from_station, to_station, date)
            result["debug_url"] = url
            result["html_length"] = len(response.text)
            return result
            
        except requests.exceptions.Timeout:
            return {"error": "Request timeout", "trains": []}
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "trains": []}
    
    def _parse_trains(self, html: str, source: str, destination: str, date: str):
        """Parse train data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        trains = []
        
        all_text = soup.get_text()
        
        train_pattern = re.compile(r'(\d{5})[\s\-]*(.+?)\s*(\d{2}:\d{2})\s*[\->‑]+\s*(\d{2}:\d{2})')
        matches = train_pattern.findall(all_text)
        
        if matches:
            for match in matches[:15]:
                train_number, train_name, depart, arrive = match
                train_name = train_name.strip()[:40]
                
                classes = self._extract_classes_from_text(all_text, train_number)
                
                trains.append({
                    "Train No": train_number,
                    "Train Name": train_name,
                    "Departure": depart,
                    "Arrival": arrive,
                    "Duration": "",
                    **classes
                })
        
        if not trains:
            for tr in soup.find_all('tr'):
                text = tr.get_text()
                if re.search(r'\d{5}', text):
                    num_match = re.search(r'(\d{5})', text)
                    if num_match:
                        train_number = num_match.group(1)
                        name_match = re.search(r'[A-Z][a-z].+?(?=\d{2}:)', text)
                        train_name = name_match.group(0).strip()[:40] if name_match else ""
                        
                        if train_number and train_name:
                            classes = self._extract_classes_from_text(text, train_number)
                            trains.append({
                                "Train No": train_number,
                                "Train Name": train_name,
                                "Departure": "",
                                "Arrival": "",
                                "Duration": "",
                                **classes
                            })
        
        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains": trains[:20],
            "timestamp": datetime.now().isoformat(),
            "debug_trains_found": len(trains)
        }
    
    def _extract_classes_from_text(self, text: str, train_num: str):
        """Extract class availability from text"""
        classes = {}
        text = text.upper()
        
        class_patterns = {
            'SL': r'SL[:\s]*([A-Z]+\s*\d*|CNF|WL\s*\d+|REGRET)?',
            '3A': r'3A[:\s]*([A-Z]+\s*\d*|CNF|WL\s*\d+|REGRET)?',
            '2A': r'2A[:\s]*([A-Z]+\s*\d*|CNF|WL\s*\d+|REGRET)?',
            '1A': r'1A[:\s]*([A-Z]+\s*\d*|CNF|WL\s*\d+|REGRET)?',
            'CC': r'CC[:\s]*([A-Z]+\s*\d*|CNF|WL\s*\d+)?',
        }
        
        section_match = re.search(rf'{train_num}.+?(?=\d{{5}}|$)', text[:5000], re.DOTALL)
        if section_match:
            section = section_match.group(0)
            
            if 'CNF' in section or 'CONFIRM' in section:
                classes['Status'] = 'Available'
            elif 'WL' in section:
                wl = re.search(r'WL\s*(\d+)', section)
                classes['Status'] = f"WL {wl.group(1)}" if wl else "Waitlist"
            elif 'REGRET' in section:
                classes['Status'] = 'Regret'
            else:
                classes['Status'] = 'Check'
        
        return classes


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
    with st.spinner("Searching trains..."):
        scraper = TrainScraper()
        result = scraper.search_trains(from_station, to_station, date_str)
        
        st.write("### Debug Info")
        st.write(f"**URL:** {result.get('debug_url', 'N/A')}")
        st.write(f"**HTML Length:** {result.get('html_length', 'N/A')}")
        st.write(f"**Trains Found:** {result.get('debug_trains_found', 0)}")
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        elif result.get("trains"):
            st.success(f"Found {len(result['trains'])} trains!")
            
            df = pd.DataFrame(result["trains"])
            
            cols_order = ["Train No", "Train Name", "Departure", "Arrival", "Duration", "Status"]
            available_cols = [c for c in cols_order if c in df.columns]
            other_cols = [c for c in df.columns if c not in cols_order]
            df = df[available_cols + other_cols]
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            with st.expander("View Raw Data"):
                st.json(result)
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
