import asyncio
import os
import sys
import time
from PIL import Image
from playwright.async_api import async_playwright

async def generate_presentation_pdf():
    print("🚀 Initializing Playwright Headless Browser...")
    
    # We will save screenshots here
    screenshots = []
    total_slides = 9
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 16:9 ratio for perfect presentation slides
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Load the local HTML file directly
        file_url = f"file://{os.path.abspath('index.html')}"
        print(f"🌍 Loading presentation: {file_url}")
        
        await page.goto(file_url, wait_until="networkidle")
        
        # Wait a moment for particles/3D to initialize
        await asyncio.sleep(2)
        
        print("📸 Capturing slides...")
        for i in range(total_slides):
            print(f"  -> Snapping Slide {i+1}/{total_slides}...")
            
            # Wait for any slide transition animations to finish
            await asyncio.sleep(1.5)
            
            screenshot_path = f"/tmp/slide_{i}.png"
            await page.screenshot(path=screenshot_path)
            screenshots.append(Image.open(screenshot_path).convert('RGB'))
            
            # Click next (simulate ArrowRight or click)
            if i < total_slides - 1:
                await page.keyboard.press("ArrowRight")
        
        await browser.close()
    
    # Compile images to PDF
    print("📑 Stitching images into Enigma_AI_Presentation.pdf...")
    pdf_path = os.path.abspath("Enigma_AI_Presentation.pdf")
    if screenshots:
        screenshots[0].save(
            pdf_path,
            save_all=True,
            append_images=screenshots[1:],
            resolution=100.0
        )
        print(f"✅ Success! Presentation saved to: {pdf_path}")
    else:
        print("❌ Failed to capture slides.")

if __name__ == "__main__":
    asyncio.run(generate_presentation_pdf())
