import asyncio
from playwright.async_api import async_playwright

async def test_minimal():
    print("Starting minimal playwright test...")
    try:
        async with async_playwright() as p:
            print("Playwright started. Launching browser...")
            browser = await p.chromium.launch(headless=True)
            print("Browser launched. Opening page...")
            page = await browser.new_page()
            print("Page opened. Navigating...")
            await page.goto("http://example.com")
            print(f"Title: {await page.title()}")
            await browser.close()
            print("Test finished successfully.")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_minimal())
