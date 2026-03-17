import asyncio
from playwright.async_api import async_playwright
import re

class TrainScraper:
    def __init__(self):
        pass
    
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
        current_train = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            train_match = re.match(r'(\d{5,6})\s*(.+?)(?:\s+(CNF|WL|Regret|N/A))?\s*$', line)
            
            if train_match:
                if current_train:
                    trains.append(current_train)
                
                train_num = train_match.group(1)
                train_name = train_match.group(2).strip()[:50]
                status = train_match.group(3) if train_match.group(3) else ""
                
                current_train = {
                    "Train No": train_num,
                    "Train Name": train_name,
                    "Departure": "",
                    "Arrival": "",
                    "Duration": "",
                    "Status": status if status else "Check"
                }
                
            elif current_train and re.match(r'^\s*(?:WL|CNF|Regret|N/A|AVAILABLE)\s*\d*\s*$', line, re.IGNORECASE):
                if 'WL' in line.upper():
                    wl_match = re.search(r'WL\s*(\d+)', line, re.IGNORECASE)
                    if wl_match:
                        current_train["Status"] = f"WL {wl_match.group(1)}"
                elif 'CNF' in line.upper() or 'CONFIRM' in line.upper():
                    current_train["Status"] = "Confirm"
                elif 'REGRET' in line.upper():
                    current_train["Status"] = "Regret"
        
        if current_train:
            trains.append(current_train)
        
        if not trains:
            text_lower = text.lower()
            if 'train' in text_lower:
                parts = re.split(r'(\d{5,6})', text)
                for i in range(1, len(parts), 2):
                    if i+1 < len(parts):
                        num = parts[i]
                        name = parts[i+1].split('\n')[0][:50] if parts[i+1] else ""
                        if num and name:
                            trains.append({
                                "Train No": num,
                                "Train Name": name,
                                "Status": "Check"
                            })
        
        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains": trains[:15],
            "raw_text": text[:2000]
        }

def search_trains(from_station: str, to_station: str, date: str):
    scraper = TrainScraper()
    return asyncio.run(scraper.search_trains_async(from_station, to_station, date))


if __name__ == "__main__":
    result = search_trains("NDLS", "SBC", "18-03-2026")
    print(f"Found {len(result['trains'])} trains:")
    for t in result['trains']:
        print(f"  {t}")
