import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainScraper:
    BASE_URL = "https://www.confirmtkt.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def get_station_code(self, station_name: str) -> Optional[str]:
        """Get station code from name"""
        try:
            url = f"{self.BASE_URL}/stations/{station_name.lower()}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                stations = soup.find_all('a', href=re.compile(r'/trains-from/'))
                if stations:
                    return stations[0].get('href', '').split('/')[-1]
        except Exception as e:
            logger.error(f"Error getting station code: {e}")
        return station_name.upper() if station_name else None
    
    def search_trains(self, from_station: str, to_station: str, date: str) -> Dict:
        """
        Search trains between stations
        date format: DD-MM-YYYY
        """
        from_code = self.get_station_code(from_station)
        to_code = self.get_station_code(to_station)
        
        if not from_code or not to_code:
            return {"error": "Invalid station codes", "trains": []}
        
        url = f"{self.BASE_URL}/rbooking/trains/from/{from_code}/to/{to_code}/{date}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return self._parse_trains(response.text, from_station, to_station, date)
        except requests.RequestException as e:
            logger.error(f"Error fetching trains: {e}")
            return {"error": str(e), "trains": []}
    
    def _parse_trains(self, html: str, source: str, destination: str, date: str) -> Dict:
        """Parse train data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        trains = []
        
        train_cards = soup.find_all('div', class_=re.compile(r'train-card|train-card-wrap|trainListBox'))
        
        for card in train_cards:
            try:
                train = self._extract_train_data(card)
                if train:
                    trains.append(train)
            except Exception as e:
                logger.debug(f"Error parsing train card: {e}")
                continue
        
        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains": trains,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_train_data(self, card) -> Optional[Dict]:
        """Extract data from a single train card"""
        try:
            train_info = card.find(class_=re.compile(r'train-name|trainNum'))
            if not train_info:
                return None
            
            train_number = ""
            train_name = ""
            
            num_elem = card.find(class_=re.compile(r'train-number|num')) or card.find('span', class_='bold')
            if num_elem:
                train_number = num_elem.get_text(strip=True)
            
            name_elem = card.find(class_=re.compile(r'train-name|train-title'))
            if name_elem:
                train_name = name_elem.get_text(strip=True)
            
            if not train_number:
                return None
            
            times = card.find_all(class_=re.compile(r'time|departure|arrival'))
            departure = times[0].get_text(strip=True) if times else ""
            arrival = times[-1].get_text(strip=True) if len(times) > 1 else ""
            
            duration_elem = card.find(class_=re.compile(r'duration|time-dur'))
            duration = duration_elem.get_text(strip=True) if duration_elem else ""
            
            classes = self._extract_classes(card)
            
            return {
                "train_number": train_number,
                "train_name": train_name,
                "departure": departure,
                "arrival": arrival,
                "duration": duration,
                "classes": classes
            }
        except Exception as e:
            logger.debug(f"Error extracting train: {e}")
            return None
    
    def _extract_classes(self, card) -> Dict:
        """Extract class availability"""
        classes = {}
        
        class_boxes = card.find_all(class_=re.compile(r'class-box|class-info|booking|seat-availability'))
        
        class_mapping = {
            'SL': 'Sleeper',
            '3A': '3 AC',
            '2A': '2 AC',
            '1A': '1 AC',
            'CC': 'Chair Car',
            '3E': '3 AC Economy',
            '2S': 'Second Sitting'
        }
        
        for box in class_boxes:
            text = box.get_text(strip=True)
            
            for code, name in class_mapping.items():
                if code in text.upper():
                    status = self._parse_status(text)
                    classes[code] = {
                        "name": name,
                        "status": status,
                        "price": self._parse_price(text),
                        "waitlist": self._parse_wl(text),
                        "chance": self._parse_chance(text)
                    }
        
        return classes
    
    def _parse_status(self, text: str) -> str:
        text = text.upper()
        if 'CONFIRM' in text or 'CNF' in text:
            return "Confirm"
        elif 'WL' in text or 'WAITLIST' in text:
            return "Waitlist"
        elif 'REGRET' in text or 'NO BOOKING' in text:
            return "Regret"
        elif 'NOT AVAILABLE' in text:
            return "Not Available"
        return "Unknown"
    
    def _parse_price(self, text: str) -> Optional[int]:
        match = re.search(r'₹?(\d+)', text)
        return int(match.group(1)) if match else None
    
    def _parse_wl(self, text: str) -> Optional[int]:
        match = re.search(r'WL\s*(\d+)', text, re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    def _parse_chance(self, text: str) -> Optional[int]:
        match = re.search(r'(\d+)%', text)
        return int(match.group(1)) if match else None


if __name__ == "__main__":
    scraper = TrainScraper()
    result = scraper.search_trains("NDLS", "BSB", "20-03-2026")
    print(result)
