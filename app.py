import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time

from scraper import scrape_product_from_url

def get_sitemap_urls():
    """Extract product URLs from Poltrona Frau sitemap."""
    try:
        response = requests.get('https://www.poltronafrau.com/ww/en/sitemap.xml', timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        urls = []
        
        # Extract URLs from sitemap
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_elem is not None:
                url = loc_elem.text
                # Only include product URLs
                if '/ww/en/products/' in url:
                    urls.append(url)
        
        return urls
    except Exception as e:
        st.error(f"Error fetching sitemap: {e}")
        return []

def scrape_single_url(url):
    """Scrape a single URL and return the data."""
    try:
        with st.spinner(f'Scraping {url}...'):
            data = scrape_product_from_url(url, save_to_json=False)
            return data
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None

def scrape_multiple_urls(urls):
    """Scrape multiple URLs and return combined data."""
    all_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, url in enumerate(urls):
        status_text.text(f'Scraping {i+1}/{len(urls)}: {url}')
        try:
            data = scrape_product_from_url(url, save_to_json=False)
            if data:
                all_data.append(data)
        except Exception as e:
            st.warning(f"Failed to scrape {url}: {e}")
        
        progress_bar.progress((i + 1) / len(urls))
        time.sleep(1)  # Be respectful to the server
    
    status_text.text(f'Completed scraping {len(all_data)} products')
    return all_data

def convert_to_csv(data_list):
    """Convert scraped data to CSV format."""
    if not data_list:
        return None
    
    # Flatten the data for CSV export
    flattened_data = []
    
    for item in data_list:
        flat_item = {
            'url': item.get('url', ''),
            'product_name': item.get('product_name', ''),
            'sku': item.get('sku', ''),
            'product_description': item.get('product_description', ''),
            'concept_and_design': item.get('concept_and_design', ''),
            'breadcrumbs': ' > '.join(item.get('breadcrumbs', [])),
            'designer_name': item.get('designer', {}).get('name', ''),
            'designer_bio': item.get('designer', {}).get('bio', ''),
            'designer_image': item.get('designer', {}).get('image', ''),
            'hero_images_count': len(item.get('images', {}).get('hero_images', [])),
            'product_images_count': len(item.get('images', {}).get('product_images', [])),
            'contextual_images_count': len(item.get('images', {}).get('contextual_images', [])),
            'dimension_images_count': len(item.get('images', {}).get('dimension_images', [])),
            'downloads_count': len(item.get('downloads', [])),
            'coverings_materials': ', '.join(item.get('coverings_and_finishes', {}).keys())
        }
        flattened_data.append(flat_item)
    
    return pd.DataFrame(flattened_data)

def main():
    st.set_page_config(
        page_title="Poltrona Frau Scraper",
        page_icon="🪑",
        layout="wide"
    )
    
    st.title("🪑 Poltrona Frau Product Scraper")
    st.markdown("Extract product data from Poltrona Frau website")
    
    # Sidebar for navigation
    st.sidebar.title("Scraping Options")
    scrape_mode = st.sidebar.radio(
        "Choose scraping mode:",
        ["Single URL", "Multiple URLs", "All Products (Sitemap)"]
    )
    
    if scrape_mode == "Single URL":
        st.header("Single URL Scraping")
        
        url = st.text_input(
            "Enter Poltrona Frau product URL:",
            placeholder="https://www.poltronafrau.com/ww/en/products/..."
        )
        
        if st.button("Scrape Product", type="primary"):
            if url and '/ww/en/products/' in url:
                data = scrape_single_url(url)
                if data:
                    # Store data in session state
                    st.session_state.scraped_data = data
                    st.session_state.scrape_mode = "single"
                    st.success("✅ Product scraped successfully!")
            else:
                st.error("Please enter a valid Poltrona Frau product URL")
        
        # Display scraped data if it exists in session state
        if 'scraped_data' in st.session_state and st.session_state.scrape_mode == "single":
            data = st.session_state.scraped_data
            
            # Display basic info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Product Name", data.get('product_name', 'N/A'))
                st.metric("SKU", data.get('sku', 'N/A'))
            with col2:
                st.metric("Designer", data.get('designer', {}).get('name', 'N/A'))
                st.metric("Images Found", len([img for category in data.get('images', {}).values() for img in category]))
            
            # Export options
            st.subheader("Export Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📄 Download JSON",
                    data=json_str,
                    file_name=f"{data.get('sku', 'product')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                csv_df = convert_to_csv([data])
                if csv_df is not None:
                    csv_buffer = io.StringIO()
                    csv_df.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📊 Download CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"{data.get('sku', 'product')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("🗑️ Clear Data"):
                    del st.session_state.scraped_data
                    del st.session_state.scrape_mode
                    st.rerun()
            
            # Show raw data
            with st.expander("View Raw Data"):
                st.json(data)
    
    elif scrape_mode == "Multiple URLs":
        st.header("Multiple URLs Scraping")
        
        urls_text = st.text_area(
            "Enter URLs (one per line):",
            placeholder="https://www.poltronafrau.com/ww/en/products/product1.html\nhttps://www.poltronafrau.com/ww/en/products/product2.html",
            height=150
        )
        
        if st.button("Scrape All URLs", type="primary"):
            if urls_text:
                urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
                valid_urls = [url for url in urls if '/ww/en/products/' in url]
                
                if valid_urls:
                    st.info(f"Found {len(valid_urls)} valid URLs to scrape")
                    data_list = scrape_multiple_urls(valid_urls)
                    
                    if data_list:
                        # Store data in session state
                        st.session_state.scraped_data = data_list
                        st.session_state.scrape_mode = "multiple"
                        st.success(f"✅ Successfully scraped {len(data_list)} products!")
                else:
                    st.error("No valid Poltrona Frau product URLs found")
            else:
                st.error("Please enter at least one URL")
        
        # Display scraped data if it exists in session state
        if 'scraped_data' in st.session_state and st.session_state.scrape_mode == "multiple":
            data_list = st.session_state.scraped_data
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Products Scraped", len(data_list))
            with col2:
                st.metric("Total Images", sum(len([img for category in item.get('images', {}).values() for img in category]) for item in data_list))
            with col3:
                st.metric("Total Downloads", sum(len(item.get('downloads', [])) for item in data_list))
            
            # Export options
            st.subheader("Export All Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                json_str = json.dumps(data_list, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📄 Download All JSON",
                    data=json_str,
                    file_name=f"poltrona_frau_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                csv_df = convert_to_csv(data_list)
                if csv_df is not None:
                    csv_buffer = io.StringIO()
                    csv_df.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📊 Download All CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"poltrona_frau_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("🗑️ Clear Data", key="clear_multiple"):
                    del st.session_state.scraped_data
                    del st.session_state.scrape_mode
                    st.rerun()
    
    elif scrape_mode == "All Products (Sitemap)":
        st.header("Scrape All Products from Sitemap")
        st.warning("⚠️ This will scrape ALL products from the website. This may take a very long time!")
        
        if st.button("Load Sitemap URLs"):
            with st.spinner("Fetching sitemap..."):
                sitemap_urls = get_sitemap_urls()
            
            if sitemap_urls:
                st.success(f"Found {len(sitemap_urls)} product URLs in sitemap")
                st.session_state.sitemap_urls = sitemap_urls
                
                # Show first few URLs as preview
                with st.expander("Preview URLs (first 10)"):
                    for url in sitemap_urls[:10]:
                        st.text(url)
                    if len(sitemap_urls) > 10:
                        st.text(f"... and {len(sitemap_urls) - 10} more")
        
        if 'sitemap_urls' in st.session_state:
            st.info(f"Ready to scrape {len(st.session_state.sitemap_urls)} products")
            
            if st.button("🚀 Scrape All Products", type="primary"):
                data_list = scrape_multiple_urls(st.session_state.sitemap_urls)
                
                if data_list:
                    # Store data in session state
                    st.session_state.scraped_data = data_list
                    st.session_state.scrape_mode = "sitemap"
                    st.success(f"✅ Successfully scraped {len(data_list)} products!")
        
        # Display scraped data if it exists in session state
        if 'scraped_data' in st.session_state and st.session_state.scrape_mode == "sitemap":
            data_list = st.session_state.scraped_data
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Products Scraped", len(data_list))
            with col2:
                st.metric("Total Images", sum(len([img for category in item.get('images', {}).values() for img in category]) for item in data_list))
            with col3:
                st.metric("Total Downloads", sum(len(item.get('downloads', [])) for item in data_list))
            with col4:
                st.metric("Unique Designers", len(set(item.get('designer', {}).get('name', '') for item in data_list if item.get('designer', {}).get('name'))))
            
            # Export options
            st.subheader("Export Complete Dataset")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                json_str = json.dumps(data_list, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📄 Download Complete JSON",
                    data=json_str,
                    file_name=f"poltrona_frau_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                csv_df = convert_to_csv(data_list)
                if csv_df is not None:
                    csv_buffer = io.StringIO()
                    csv_df.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📊 Download Complete CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"poltrona_frau_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("🗑️ Clear Data", key="clear_sitemap"):
                    del st.session_state.scraped_data
                    del st.session_state.scrape_mode
                    st.rerun()

if __name__ == "__main__":
    main()