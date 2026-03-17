import asyncio
from playwright.async_api import async_playwright
import sys

async def test_search():
    url = "https://www.confirmtkt.com/rbooking/trains/from/NDLS/to/SBC/18-03-2026"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print("Loading page...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        print("Waiting for trains...")
        await page.wait_for_timeout(15000)
        
        text = await page.evaluate("document.body.innerText")
        print(f"Text length: {len(text)}")
        
        # Write to file to avoid encoding issues
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(text[:5000])
        print("Saved to output.txt")
        
        # Try to find train-related content
        lines = text.split('\n')
        train_lines = [l for l in lines if any(x in l for x in ['Train', 'CNF', 'WL', 'Express', 'Departs', 'Arrives'])]
        for l in train_lines[:15]:
            print(l[:100])
        
        await browser.close()

asyncio.run(test_search())
