from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
from urllib.parse import urlparse
import time

def setup_driver():
    """Setup Chrome driver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def download_rendered_html(driver, url, output_dir):
    """Download rendered HTML from a URL and save it to the output directory."""
    try:
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(3)
        
        # Get the rendered HTML
        rendered_html = driver.page_source
        
        # Generate filename from URL
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        if not filename or filename == '/':
            filename = 'index'
        if not filename.endswith('.html'):
            filename += '.html'
        
        filepath = os.path.join(output_dir, filename)
        
        # Save the rendered HTML
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        
        print(f"Downloaded: {url} -> {filepath}")
        return True
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    urls_file = 'reference/tests/test_urls.txt'
    output_dir = 'reference/tests'
    
    if not os.path.exists(urls_file):
        print(f"Error: {urls_file} not found")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Read URLs from file
    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(urls)} URLs to download")
    
    # Setup Selenium driver
    driver = setup_driver()
    
    try:
        for i, url in enumerate(urls, 1):
            print(f"Processing {i}/{len(urls)}: {url}")
            download_rendered_html(driver, url, output_dir)
            time.sleep(2)  # Be respectful to the server
        
        print("Download complete!")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()