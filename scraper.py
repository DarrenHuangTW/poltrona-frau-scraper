from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import re
import os
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class PoltronaFrauScraper:
    """Scraper for extracting product data from Poltrona Frau product pages using Selenium."""
    
    def __init__(self, driver: webdriver.Chrome, url: str):
        """
        Initialize the scraper with a Selenium WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance with the page already loaded
            url: The original URL of the product page
        """
        self.driver = driver
        self.url = url
        self.base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        self.wait = WebDriverWait(driver, 10)
    
    def extract_url(self) -> str:
        """Extract the product URL."""
        return self.url
    
    def extract_product_name(self) -> Optional[str]:
        """
        Extract the product name from the page.
        
        Returns:
            Product name or None if not found
        """
        try:
            # Try to find product name in h1 with class cmp-producthero__productName
            product_name_h1 = self.driver.find_element(By.CSS_SELECTOR, 'h1.cmp-producthero__productName span')
            return product_name_h1.text.strip()
        except NoSuchElementException:
            pass
        
        try:
            # Fallback: try to get from data attributes
            product_form = self.driver.find_element(By.CSS_SELECTOR, 'form[data-product-name]')
            return product_form.get_attribute('data-product-name')
        except NoSuchElementException:
            pass
        
        try:
            # Fallback: try to get from JSON-LD breadcrumb data
            breadcrumb_script = self.driver.find_element(By.ID, 'jsonldBreadcrumb')
            breadcrumb_data = json.loads(breadcrumb_script.get_attribute('innerHTML'))
            items = breadcrumb_data.get('itemListElement', [])
            if items:
                # Last item should be the product name
                return items[-1].get('item', {}).get('name')
        except (NoSuchElementException, json.JSONDecodeError, AttributeError):
            pass
        
        return None
    
    def extract_sku(self) -> Optional[str]:
        """
        Extract the SKU from the page.
        
        Returns:
            SKU (7 digits) or None if not found
        """
        try:
            # Look for data-product-sku attribute on div.product.product-configurator-aem
            product_div = self.driver.find_element(By.CSS_SELECTOR, 'div.product.product-configurator-aem')
            sku = product_div.get_attribute('data-product-sku')
            if sku:
                return sku
        except NoSuchElementException:
            pass
        
        try:
            # Fallback: look for data-product-sku on form element
            product_form = self.driver.find_element(By.CSS_SELECTOR, 'form[data-product-sku]')
            return product_form.get_attribute('data-product-sku')
        except NoSuchElementException:
            pass
        
        return None
    
    def extract_designer(self) -> Optional[str]:
        """
        Extract the designer name from the page.
        
        Returns:
            Designer name or None if not found
        """
        try:
            # Try to find designer in h3 with class cmp-producthero__productDesigner
            designer_h3 = self.driver.find_element(By.CSS_SELECTOR, 'h3.cmp-producthero__productDesigner')
            return designer_h3.text.strip()
        except NoSuchElementException:
            pass
        
        try:
            # Fallback: try to get from data attributes
            product_form = self.driver.find_element(By.CSS_SELECTOR, 'form[data-product-designer]')
            return product_form.get_attribute('data-product-designer')
        except NoSuchElementException:
            pass
        
        return None
    
    def extract_breadcrumbs(self) -> List[Dict[str, str]]:
        """
        Extract breadcrumb navigation from the page.
        
        Returns:
            List of breadcrumb items with 'name' and 'url' keys
        """
        breadcrumbs = []
        
        try:
            # Try to get from JSON-LD structured data first (most reliable)
            breadcrumb_script = self.driver.find_element(By.ID, 'jsonldBreadcrumb')
            breadcrumb_data = json.loads(breadcrumb_script.get_attribute('innerHTML'))
            items = breadcrumb_data.get('itemListElement', [])
            for item in items:
                item_data = item.get('item', {})
                breadcrumbs.append({
                    'name': item_data.get('name', ''),
                    'url': item_data.get('@id', '')
                })
            return breadcrumbs
        except (NoSuchElementException, json.JSONDecodeError, AttributeError):
            pass
        
        try:
            # Fallback: parse HTML breadcrumb structure
            breadcrumb_nav = self.driver.find_element(By.CSS_SELECTOR, 'nav.cmp-breadcrumb')
            breadcrumb_items = breadcrumb_nav.find_elements(By.CSS_SELECTOR, 'li.cmp-breadcrumb__item')
            for item in breadcrumb_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.cmp-breadcrumb__item-link')
                    span = link.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]')
                    breadcrumbs.append({
                        'name': span.text.strip(),
                        'url': link.get_attribute('href')
                    })
                except NoSuchElementException:
                    # This might be the current page (no link)
                    try:
                        span = item.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]')
                        breadcrumbs.append({
                            'name': span.text.strip(),
                            'url': self.url
                        })
                    except NoSuchElementException:
                        continue
        except NoSuchElementException:
            pass
        
        return breadcrumbs
    
    def extract_product_description(self) -> Optional[str]:
        """
        Extract the product description from div.productcontents using static extraction.
        
        Returns:
            Product description or None if not found
        """
        try:
            # Use JavaScript to get innerHTML content (Selenium .text doesn't work for this element)
            description = self.driver.execute_script(
                'return document.querySelector(".cmp-productcontents .cmp-text p")?.innerHTML?.trim() || null;'
            )
            if description and len(description) > 20:
                # Clean HTML tags if any
                import re
                clean_text = re.sub(r'<[^>]+>', '', description).strip()
                return clean_text
        except Exception:
            pass
        
        try:
            # Fallback: try alternative selector with JavaScript
            description = self.driver.execute_script(
                'var elements = document.querySelectorAll(".cmp-productcontents p"); ' +
                'for (var i = 0; i < elements.length; i++) { ' +
                '  var text = elements[i].innerHTML?.trim(); ' +
                '  if (text && text.length > 20) return text; ' +
                '} return null;'
            )
            if description:
                # Clean HTML tags if any
                import re
                clean_text = re.sub(r'<[^>]+>', '', description).strip()
                return clean_text
        except Exception:
            pass
        
        return None
    
    def extract_designer_bio(self) -> Optional[str]:
        """
        Extract designer biography from the page using static extraction.
        
        Returns:
            Designer bio text or None if not found
        """
        try:
            # Use JavaScript to get innerHTML content (Selenium .text doesn't work for this element)
            bio_text = self.driver.execute_script(
                'return document.querySelector("div.text.paneltext p")?.innerHTML?.trim() || null;'
            )
            if bio_text and len(bio_text) > 100:  # Bio should be substantial
                # Clean HTML tags if any
                import re
                clean_text = re.sub(r'<[^>]+>', '', bio_text).strip()
                return clean_text
        except Exception:
            pass
        
        try:
            # Fallback: try alternative selectors with JavaScript
            fallback_selectors = [
                '.paneltext p',
                '.text.paneltext',
                '[class*="paneltext"] p'
            ]
            
            for selector in fallback_selectors:
                try:
                    bio_text = self.driver.execute_script(
                        f'return document.querySelector("{selector}")?.innerHTML?.trim() || null;'
                    )
                    if bio_text and len(bio_text) > 100:
                        # Clean HTML tags if any
                        import re
                        clean_text = re.sub(r'<[^>]+>', '', bio_text).strip()
                        return clean_text
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def extract_designer_image(self) -> Optional[str]:
        """
        Extract designer image URL from the page using static extraction.
        
        Returns:
            Designer image URL or None if not found
        """
        try:
            # Direct static extraction - try specific designer image selectors
            designer_selectors = [
                'img[src*="tab-designer"]',
                'img[data-src*="tab-designer"]',
                'img[src*="designer"]',
                'img[data-src*="designer"]'
            ]
            
            for selector in designer_selectors:
                try:
                    img_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    img_url = img_element.get_attribute('src') or img_element.get_attribute('data-src')
                    if img_url:
                        # Convert relative URLs to absolute
                        if img_url.startswith('//'):
                            img_url = f"https:{img_url}"
                        elif img_url.startswith('/'):
                            img_url = urljoin(self.base_url, img_url)
                        return img_url
                except NoSuchElementException:
                    continue
        except Exception:
            pass
        
        try:
            # Fallback: search for designer name in image URLs
            all_images = self.driver.find_elements(By.CSS_SELECTOR, 'img[src], img[data-src]')
            for img in all_images:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if src and ('massaud' in src.lower() or 'lazzeroni' in src.lower() or 'designer' in src.lower()):
                    # Convert relative URLs to absolute
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = urljoin(self.base_url, src)
                    return src
        except Exception:
            pass
        
        return None
    
    def extract_downloads(self) -> List[Dict[str, str]]:
        """
        Extract downloads/files from the Downloads section using static Selenium extraction.
        
        Returns:
            List of download items with group, filename, and URL
        """
        downloads = []
        
        try:
            # Direct extraction from static HTML - no tab interaction needed
            # Find all download links with data-href attributes (works even for hidden elements)
            download_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-href]')
            
            for link in download_links:
                data_href = link.get_attribute('data-href')
                
                if data_href:
                    download_title = None
                    
                    # Method 1: Look for accordion title in subitem structure (for 2D/3D planning tools)
                    try:
                        parent_subitem = link.find_element(By.XPATH, './ancestor::div[contains(@class, "cmp-accordion__subitem")]')
                        title_element = parent_subitem.find_element(By.CSS_SELECTOR, 'span.cmp-accordion__title')
                        download_title = title_element.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    # Method 2: Look for title in parent flex div
                    if not download_title:
                        try:
                            flex_parent = link.find_element(By.XPATH, './ancestor::div[contains(@class, "flex")]')
                            title_element = flex_parent.find_element(By.CSS_SELECTOR, 'span.cmp-accordion__title')
                            download_title = title_element.text.strip()
                        except NoSuchElementException:
                            pass
                    
                    # Method 3: Look for title in button parent (for header-level downloads like Product sheet, Dimensions, Gallery)
                    if not download_title:
                        try:
                            button_parent = link.find_element(By.XPATH, './ancestor::button[contains(@class, "cmp-accordion__button")]')
                            title_element = button_parent.find_element(By.CSS_SELECTOR, 'span.cmp-accordion__title')
                            download_title = title_element.text.strip()
                        except NoSuchElementException:
                            pass
                    
                    # Method 4: Extract from filename as last resort
                    if not download_title:
                        url_parts = data_href.split('/')
                        filename_part = url_parts[-1] if url_parts else ''
                        if '_' in filename_part:
                            download_title = filename_part.split('_')[-1].split('.')[0].upper()
                        else:
                            download_title = 'Unknown Download'
                    
                    if download_title and data_href:
                        # Convert to uppercase for standardization
                        group_name = download_title.upper()
                        
                        # Convert relative URL to absolute URL
                        if data_href.startswith('/'):
                            absolute_url = urljoin(self.base_url, data_href)
                        else:
                            absolute_url = data_href
                        
                        downloads.append({
                            'group': group_name,
                            'url': absolute_url
                        })
            
            # Remove duplicates
            unique_downloads = []
            seen = set()
            
            for download in downloads:
                key = f"{download['group']}|{download['url']}"
                
                # Skip empty or invalid entries
                if not download['group'] or download['group'].strip() == '' or 'UNDEFINED' in download['group']:
                    continue
                
                if key not in seen:
                    seen.add(key)
                    unique_downloads.append(download)
            
            return unique_downloads
        
        except Exception as e:
            print(f"Error in downloads extraction: {e}")
            return []
    
    
    def extract_coverings_and_finishes(self) -> Dict[str, Any]:
        """
        Extract coverings and finishes data by fetching the separate HTML file from data-include.
        
        Returns:
            Dict with 3-layer structure: material_type > category > individual finishes
        """
        finishes_data = {}
        
        try:
            # Direct extraction of data-include URL from static HTML - no interaction needed
            try:
                include_element = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    '#finishes-tab-positioning-bottom[data-include]'
                )
                include_url = include_element.get_attribute('data-include')
            except NoSuchElementException:
                # Fallback: look for any element with data-include in finishes context
                try:
                    include_element = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        '[data-include*="finishes"]'
                    )
                    include_url = include_element.get_attribute('data-include')
                except NoSuchElementException:
                    print("No data-include URL found for finishes content")
                    return finishes_data
            
            if include_url:
                # Convert relative URL to absolute URL
                from urllib.parse import urljoin
                if include_url.startswith('/'):
                    full_url = urljoin(self.base_url, include_url)
                else:
                    full_url = include_url
                
                print(f"Fetching finishes content from: {full_url}")
                
                # Fetch the separate HTML file
                import requests
                response = requests.get(full_url)
                
                if response.status_code == 200:
                    finishes_html = response.text
                    
                    # Parse the fetched HTML using BeautifulSoup
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(finishes_html, 'html.parser')
                    
                    # Extract material type tabs from <ol role="tablist">
                    tablist = soup.find('ol', {'role': 'tablist'})
                    if tablist:
                        material_tabs = tablist.find_all('li', {'role': 'tab'})
                        
                        for tab in material_tabs:
                            material_type = tab.get_text(strip=True).upper()
                            tab_id = tab.get('id', '')
                            
                            if material_type and tab_id:
                                # Find corresponding panel (div id="0", "1", "2", etc.)
                                panel_id = tab_id.split('-')[0]  # Extract "0" from "0-tab"
                                panel = soup.find('div', id=panel_id)
                                
                                if panel:
                                    # Find accordion headers (categories) within this material panel
                                    accordion_headers = panel.find_all('h3', class_='cmp-accordion__header')
                                    
                                    for header in accordion_headers:
                                        # Extract category name from span.cmp-accordion__title
                                        title_span = header.find('span', class_='cmp-accordion__title')
                                        category_name = title_span.get_text(strip=True) if title_span else 'Unknown Category'
                                        
                                        # Find the accordion item containing this header
                                        accordion_item = header.find_parent(class_='cmp-accordion__item')
                                        if accordion_item:
                                            # Find all finish grid cells within this accordion item
                                            grid_cells = accordion_item.find_all('div', class_='finishes__grid-cell')
                                            
                                            for cell in grid_cells:
                                                # Extract image with data-src
                                                img = cell.find('img', {'data-src': True})
                                                if img:
                                                    # Get image URL and make it full URL
                                                    image_url = img.get('data-src', '')
                                                    if '/jcr:content' in image_url:
                                                        image_url = image_url.split('/jcr:content')[0]
                                                    
                                                    # Convert to full URL if it's relative
                                                    if image_url.startswith('/'):
                                                        from urllib.parse import urljoin
                                                        image_url = urljoin(self.base_url, image_url)
                                                    
                                                    # Extract color_caption from span.cmp-image__title
                                                    color_caption = ''
                                                    caption_span = cell.find('span', class_='cmp-image__title')
                                                    if caption_span:
                                                        color_caption = caption_span.get_text(strip=True)
                                                    
                                                    # Extract color_name from div.cmp-text within finishes__grid-cell-text
                                                    color_name = ''
                                                    text_cell = cell.find_next_sibling('div', class_='finishes__grid-cell-text')
                                                    if text_cell:
                                                        text_div = text_cell.find('div', class_='cmp-text')
                                                        if text_div:
                                                            color_name = text_div.get_text(strip=True)
                                                    
                                                    # Also check if the text cell is within the same cell (not sibling)
                                                    if not color_name:
                                                        text_cell = cell.find('div', class_='finishes__grid-cell-text')
                                                        if text_cell:
                                                            text_div = text_cell.find('div', class_='cmp-text')
                                                            if text_div:
                                                                color_name = text_div.get_text(strip=True)
                                                    
                                                    if image_url:
                                                        # Initialize material_type if not exists
                                                        if material_type not in finishes_data:
                                                            finishes_data[material_type] = {}
                                                        
                                                        # Initialize category if not exists
                                                        if category_name not in finishes_data[material_type]:
                                                            finishes_data[material_type][category_name] = []
                                                        
                                                        # Add finish to the appropriate category
                                                        finishes_data[material_type][category_name].append({
                                                            'color_caption': color_caption,
                                                            'color_name': color_name,
                                                            'color_url': image_url
                                                        })
                    
                    # Fallback: if no structured data found, do a general search
                    if not finishes_data:
                        print("No structured data found, falling back to general search...")
                        all_images = soup.find_all('img', {'data-src': True})
                        for img in all_images:
                            image_url = img.get('data-src', '')
                            if '/jcr:content' in image_url:
                                image_url = image_url.split('/jcr:content')[0]
                            
                            name = img.get('alt', 'Finish Item')
                            
                            # Add to fallback structure
                            if 'Unknown' not in finishes_data:
                                finishes_data['Unknown'] = {}
                            if 'General' not in finishes_data['Unknown']:
                                finishes_data['Unknown']['General'] = []
                            
                            finishes_data['Unknown']['General'].append({
                                'color_caption': '',
                                'color_name': name,
                                'color_url': image_url
                            })
                
                else:
                    print(f"Failed to fetch finishes HTML: {response.status_code}")
            
            else:
                print("No data-include URL found for finishes content")
            
        except Exception as e:
            print(f"Error extracting coverings and finishes: {e}")
            import traceback
            traceback.print_exc()
        
        return finishes_data
    
    def extract_concept_and_design(self) -> Optional[str]:
        """
        Extract concept and design information from meta tags.
        
        Returns:
            Concept and design text or None if not found
        """
        try:
            # Try meta description first (this contains the concept/design info)
            meta_desc = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            content = meta_desc.get_attribute('content')
            if content:
                # Decode HTML entities and remove HTML tags
                import html
                decoded = html.unescape(content)
                # Simple HTML tag removal
                import re
                clean_text = re.sub(r'<[^>]+>', '', decoded)
                return clean_text.strip()
        except NoSuchElementException:
            pass
        
        try:
            # Fallback: try og:description
            og_desc = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:description"]')
            content = og_desc.get_attribute('content')
            if content:
                import html
                decoded = html.unescape(content)
                import re
                clean_text = re.sub(r'<[^>]+>', '', decoded)
                return clean_text.strip()
        except NoSuchElementException:
            pass
        
        # Fallback: Look for concept and design content in tabs or sections
        try:
            concept_selectors = [
                '[data-tab="concept"] .text',
                '[data-tab="conceptdesign"] .text',
                '.concept-design .text',
                '.cmp-tabs__panel .text'  # Generic tab panel text
            ]
            
            for selector in concept_selectors:
                try:
                    concept_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    concept_text = concept_element.text.strip()
                    if concept_text and len(concept_text) > 50:  # Filter out short text
                        return concept_text
                except NoSuchElementException:
                    continue
        except Exception:
            pass
        
        return None
    
    def extract_images_by_category(self) -> Dict[str, List[str]]:
        """
        Extract product images organized by category.
        
        Returns:
            Dictionary with image categories and their URLs
        """
        images = {
            'hero_images': [],
            'product_images': [],
            'contextual_images': [],
            'dimension_images': []
        }
        
        def process_image_src(src):
            """Helper to process and clean image URLs"""
            if not src:
                return None
            
            # Convert relative URLs to absolute
            if src.startswith('//'):
                src = f"https:{src}"
            elif src.startswith('/'):
                src = urljoin(self.base_url, src)
            
            # Filter out placeholder/loading images and icons
            if any(placeholder in src.lower() for placeholder in ['placeholder', 'loading', 'blank', 'icon', '.svg']):
                return None
            
            return src
        
        # Hero images (main product image)
        hero_selectors = [
            '.cmp-producthero__image img',
            '.hero img',
            'img[src*="01_hero"], img[data-src*="01_hero"], img[data-lazy-src*="01_hero"]'
        ]
        
        for hero_selector in hero_selectors:
            try:
                hero_imgs = self.driver.find_elements(By.CSS_SELECTOR, hero_selector)
                for img in hero_imgs:
                    src = process_image_src(img.get_attribute('src') or 
                                          img.get_attribute('data-src') or 
                                          img.get_attribute('data-lazy-src'))
                    if src and src not in images['hero_images']:
                        images['hero_images'].append(src)
            except NoSuchElementException:
                continue
        
        # Product images (thumbnails, gallery)
        try:
            # Look for images in thumbnail galleries (02_thumbnails folder)
            product_imgs = self.driver.find_elements(By.CSS_SELECTOR, 
                'img[src*="02_thumbnails"], img[data-src*="02_thumbnails"], img[data-lazy-src*="02_thumbnails"]')
            for img in product_imgs:
                src = process_image_src(img.get_attribute('src') or 
                                      img.get_attribute('data-src') or 
                                      img.get_attribute('data-lazy-src'))
                if src and src not in images['product_images']:
                    images['product_images'].append(src)
        except NoSuchElementException:
            pass
        
        # Contextual images (concept and design section - 03_concept folder)
        try:
            contextual_imgs = self.driver.find_elements(By.CSS_SELECTOR, 
                'img[src*="03_concept"], img[data-src*="03_concept"], img[data-lazy-src*="03_concept"]')
            for img in contextual_imgs:
                src = process_image_src(img.get_attribute('src') or 
                                      img.get_attribute('data-src') or 
                                      img.get_attribute('data-lazy-src'))
                if src and src not in images['contextual_images']:
                    images['contextual_images'].append(src)
        except NoSuchElementException:
            pass
        
        # Dimension images (08_dimensioni folder)
        try:
            dimension_imgs = self.driver.find_elements(By.CSS_SELECTOR, 
                'img[src*="08_dimensioni"], img[data-src*="08_dimensioni"], img[data-lazy-src*="08_dimensioni"]')
            for img in dimension_imgs:
                src = process_image_src(img.get_attribute('src') or 
                                      img.get_attribute('data-src') or 
                                      img.get_attribute('data-lazy-src'))
                if src and src not in images['dimension_images']:
                    images['dimension_images'].append(src)
        except NoSuchElementException:
            pass
        
        return images
    
    def extract_images(self) -> List[str]:
        """
        Extract all product images from the page (for backward compatibility).
        
        Returns:
            List of all image URLs
        """
        images_by_category = self.extract_images_by_category()
        all_images = []
        
        for category, img_list in images_by_category.items():
            all_images.extend(img_list)
        
        return all_images
    
    def extract_all_data(self) -> Dict[str, Any]:
        """
        Extract all available data from the product page.
        
        Returns:
            Dictionary containing all extracted data with reorganized structure
        """
        # Extract breadcrumbs and convert to list of strings
        breadcrumbs_data = self.extract_breadcrumbs()
        breadcrumbs_text = [item['name'] for item in breadcrumbs_data]
        
        # Extract images by category
        images_by_category = self.extract_images_by_category()
        
        # Extract designer information
        designer_info = {
            'name': self.extract_designer(),
            'bio': self.extract_designer_bio(),
            'image': self.extract_designer_image()
        }
        
        # Extract downloads
        downloads = self.extract_downloads()
        
        # Extract coverings and finishes
        coverings_finishes = self.extract_coverings_and_finishes()
        
        return {
            'url': self.extract_url(),
            'product_name': self.extract_product_name(),
            'sku': self.extract_sku(),
            'product_description': self.extract_product_description(),
            'concept_and_design': self.extract_concept_and_design(),
            'breadcrumbs': breadcrumbs_text,
            'designer': designer_info,
            'images': images_by_category,
            'downloads': downloads,
            'coverings_and_finishes': coverings_finishes
        }


def setup_driver():
    """Setup Chrome driver with appropriate options for local and cloud deployment."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-images')
    
    # Check if running on Streamlit Cloud or similar environment
    import os
    if os.getenv('STREAMLIT_SHARING') or os.path.exists('/usr/bin/chromium'):
        # Use system chromium on Streamlit Cloud
        chrome_options.binary_location = '/usr/bin/chromium'
        # chromium-driver package installs to /usr/bin/chromedriver
        service = Service('/usr/bin/chromedriver')
    else:
        # Use ChromeDriverManager for local development
        service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def save_scraped_data_to_json(data: Dict[str, Any], output_dir: str = 'reference/outcomes') -> str:
    """
    Save scraped data to JSON file in the outcomes folder.
    
    Args:
        data: Dictionary containing scraped product data
        output_dir: Directory to save the JSON file
        
    Returns:
        Path to the saved JSON file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename from product name and URL
    product_name = data.get('product_name', 'unknown_product')
    sku = data.get('sku', 'unknown_sku')
    
    # Clean filename - remove special characters
    clean_name = re.sub(r'[^\w\s-]', '', product_name).strip()
    clean_name = re.sub(r'[-\s]+', '-', clean_name)
    
    # Clean SKU - remove special characters
    clean_sku = re.sub(r'[^\w-]', '', sku) if sku else 'unknown_sku'
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{clean_name}_{clean_sku}_{timestamp}.json"
    
    # Full path
    filepath = os.path.join(output_dir, filename)
    
    # Save to JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Scraped data saved to: {filepath}")
    return filepath


def scrape_product_from_url(url: str, save_to_json: bool = True) -> Dict[str, Any]:
    """
    Convenience function to scrape product data directly from a URL.
    
    Args:
        url: The URL of the product page
        save_to_json: Whether to save the results to a JSON file in reference/outcomes
        
    Returns:
        Dictionary containing all extracted data
    """
    driver = setup_driver()
    try:
        driver.get(url)
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Additional wait for dynamic content
        driver.implicitly_wait(3)
        
        scraper = PoltronaFrauScraper(driver, url)
        data = scraper.extract_all_data()
        
        # Save to JSON if requested
        if save_to_json:
            save_scraped_data_to_json(data)
        
        return data
    finally:
        driver.quit()


def scrape_product_from_file(html_file_path: str, url: str, save_to_json: bool = True) -> Dict[str, Any]:
    """
    Convenience function to scrape product data from an HTML file using Selenium.
    
    Args:
        html_file_path: Path to the HTML file
        url: The original URL of the product page
        save_to_json: Whether to save the results to a JSON file in reference/outcomes
        
    Returns:
        Dictionary containing all extracted data
    """
    driver = setup_driver()
    try:
        # Load the HTML file as a data URI to avoid file:// protocol issues
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Create a temporary file URL
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        try:
            driver.get(f"file:///{temp_file_path.replace(os.sep, '/')}")
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            scraper = PoltronaFrauScraper(driver, url)
            data = scraper.extract_all_data()
            
            # Save to JSON if requested
            if save_to_json:
                save_scraped_data_to_json(data)
            
            return data
        finally:
            os.unlink(temp_file_path)
    finally:
        driver.quit()


if __name__ == "__main__":
    # Test the scraper with URLs directly
    test_urls = [
        'https://www.poltronafrau.com/ww/en/products/the-secret-garden-small-table.html',
        'https://www.poltronafrau.com/ww/en/products/the-secret-garden-180x80-h63-table.html',
        'https://www.poltronafrau.com/ww/en/products/grantorino-hb-sofa.html'
    ]
    
    for url in test_urls:
        print(f"\n--- Scraping {url} ---")
        try:
            data = scrape_product_from_url(url)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Also test with downloaded files if you prefer
    # test_files = [
    #     {
    #         'file': 'reference/tests/the-secret-garden-small-table.html',
    #         'url': 'https://www.poltronafrau.com/ww/en/products/the-secret-garden-small-table.html'
    #     }
    # ]
    # 
    # for test_file in test_files:
    #     print(f"\n--- Scraping {test_file['file']} ---")
    #     try:
    #         data = scrape_product_from_file(test_file['file'], test_file['url'])
    #         print(json.dumps(data, indent=2, ensure_ascii=False))
    #     except Exception as e:
    #         print(f"Error scraping {test_file['file']}: {e}")