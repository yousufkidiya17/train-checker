import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import time

st.set_page_config(
    page_title="Train Availability Checker",
    page_icon="🚂",
    layout="wide"
)

st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #ff6b35;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
    }
    .stButton>button:hover {
        background-color: #ff8c5a;
    }
    .success {
        color: #28a745;
        font-weight: bold;
    }
    .waitlist {
        color: #ffc107;
        font-weight: bold;
    }
    .regret {
        color: #dc3545;
        font-weight: bold;
    }
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
        })
    
    def get_station_code(self, station_name: str) -> str:
        """Get station code from name"""
        station_name = station_name.strip().upper()
        if len(station_name) == 3:
            return station_name
        return station_name
    
    def search_trains(self, from_station: str, to_station: str, date: str):
        """Search trains between stations"""
        from_code = self.get_station_code(from_station)
        to_code = self.get_station_code(to_station)
        
        url = f"{self.BASE_URL}/rbooking/trains/from/{from_code}/to/{to_code}/{date}"
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return {"error": "Failed to fetch trains", "trains": []}
            return self._parse_trains(response.text, from_station, to_station, date)
        except Exception as e:
            return {"error": str(e), "trains": []}
    
    def _parse_trains(self, html: str, source: str, destination: str, date: str):
        """Parse train data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        trains = []
        
        train_cards = soup.find_all('div', class_=re.compile(r'train-card|train-card-wrap'))
        
        for card in train_cards:
            try:
                train = self._extract_train_data(card)
                if train:
                    trains.append(train)
            except:
                continue
        
        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains": trains,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_train_data(self, card):
        """Extract data from a single train card"""
        try:
            num_elem = card.find(class_=re.compile(r'train-number|num'))
            train_number = num_elem.get_text(strip=True) if num_elem else ""
            
            if not train_number:
                link = card.find('a', href=re.compile(r'train-'))
                if link:
                    href = link.get('href', '')
                    train_number = re.search(r'train-(\d+)', href)
                    train_number = train_number.group(1) if train_number else ""
            
            if not train_number:
                return None
            
            name_elem = card.find(class_=re.compile(r'train-name|title'))
            train_name = name_elem.get_text(strip=True)[:50] if name_elem else ""
            
            time_elems = card.find_all(class_=re.compile(r'time|departure|arrival'))
            departure = time_elems[0].get_text(strip=True) if time_elems else ""
            arrival = time_elems[-1].get_text(strip=True) if len(time_elems) > 1 else ""
            
            duration_elem = card.find(class_=re.compile(r'duration|time-dur'))
            duration = duration_elem.get_text(strip=True) if duration_elem else ""
            
            classes = self._extract_classes(card)
            
            return {
                "Train No": train_number,
                "Train Name": train_name,
                "Departure": departure,
                "Arrival": arrival,
                "Duration": duration,
                **classes
            }
        except:
            return None
    
    def _extract_classes(self, card):
        """Extract class availability"""
        classes = {}
        
        class_mapping = {
            'SL': 'Sleeper',
            '3A': '3AC', 
            '2A': '2AC',
            '1A': '1AC',
            'CC': 'Chair Car',
            '3E': '3E',
            '2S': '2S'
        }
        
        boxes = card.find_all(class_=re.compile(r'class-box|class-info|seat'))
        
        for box in boxes:
            text = box.get_text(strip=True).upper()
            for code, name in class_mapping.items():
                if code in text:
                    classes[name] = self._get_status_text(text)
                    break
        
        return classes
    
    def _get_status_text(self, text: str) -> str:
        if 'CONFIRM' in text or 'CNF' in text:
            return "✓ Confirm"
        wl = re.search(r'WL\s*(\d+)', text, re.IGNORECASE)
        if wl:
            return f"WL {wl.group(1)}"
        if 'REGRET' in text:
            return "✗ Regret"
        if 'NOT AVAILABLE' in text:
            return "-"
        return "Check"


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
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        elif result.get("trains"):
            st.success(f"Found {len(result['trains'])} trains!")
            
            df = pd.DataFrame(result["trains"])
            
            cols_order = ["Train No", "Train Name", "Departure", "Arrival", "Duration"]
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
        if st.button(label, key=f"route_{i}"):
            st.session_state.from_station = frm
            st.session_state.to_station = to

st.markdown("---")
st.caption("Data from ConfirmTkt.com | Use responsibly")
