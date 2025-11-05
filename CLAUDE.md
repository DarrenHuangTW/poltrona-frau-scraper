## Project Understanding

This project aims to build a Streamlit application for scraping product data from the Poltrona Frau website. The application will allow users to scrape data from single or multiple product URLs, as well as a "run all" feature to scrape all products from the website's sitemap. The scraped data will be exportable to JSON and CSV formats.

## Project Details

### Product URLs

- **Source of URLs:** All product URLs can be found in the website's sitemap: `https://www.poltronafrau.com/ww/en/sitemap.xml`
- **Relevant URLs:** Only URLs that contain the path `/ww/en/products/` are considered relevant for scraping.

### Technical Stack

- **Language:** Python
- **Web Scraping:** `Selenium` to get rendered HTML
- **Application Framework:** Streamlit
- **Package Management:** `uv` within a virtual environment

### Data & Error Handling

- **Data Structure:** The output data should contain all fields in the `reference/pf_data_output_v5.json` file.
- **Error Handling:** The application should handle cases where a URL is unreachable (non-200 status code) or when essential data is not found on the page.

## Scraping Research

For detailed analysis, including HTML locations and updated scraping approaches for specific data points like SKU and dynamic customization options, please refer to the research document:

- [Scraping Analysis Details](./RESEARCH.MD)

## Data Extraction Status

### ✅ Successfully Implemented

| Data Point | Status | Extraction Method | Notes |
|------------|---------|------------------|-------|
| **URL** | ✅ Complete | Direct from scraper input | Returns the product page URL |
| **Product Name** | ✅ Complete | `h1.cmp-producthero__productName span` | Extracts full product title |
| **SKU (7 digits)** | ✅ Complete | `div.product.product-configurator-aem[data-product-sku]` | Reads from data attribute |
| **Designer** | ✅ Complete | `h3.cmp-producthero__productDesigner` | Designer name extraction |
| **Breadcrumbs** | ✅ Complete | JSON-LD structured data + HTML fallback | Simplified to array of strings |
| **Product Description** | ✅ Complete | `div.productcontents .cmp-text p` | Technical product details |
| **Concept and Design** | ✅ Complete | Meta description tags | Collection concept/philosophy |
| **Designer Bio** | ✅ Complete | `div.text.paneltext p` | Personal designer biography |
| **Designer Image** | ✅ Complete | Images with "designer" or designer name in URL | Designer portrait photo |
| **Images (Organized)** | ✅ Complete | Multiple selectors by folder structure | 4 categories: hero, product, contextual, dimension |

### ✅ Recently Fixed

| Data Point | Status | Extraction Method | Notes |
|------------|---------|------------------|-------|
| **Downloads** | ✅ Complete | JavaScript extraction from Downloads tab | Finds and extracts download items like 2D/3D, Product sheet, DWG files, etc. |

### ✅ Recently Completed

| Data Point | Status | Extraction Method | Notes |
|------------|---------|------------------|-------|
| **Coverings & Finishes** | ✅ Complete | 3-layer grouped structure from lazy-loaded HTML | Organized by material_type > category > individual finishes |

### 🔶 Partially Implemented

| Data Point | Status | Notes |
|------------|---------|-------|
| **Customization** | 🔶 Partial | Not yet implemented - requires configurator analysis |

### 📊 Data Structure (Final Output)

```json
{
  "url": "https://www.poltronafrau.com/...",
  "product_name": "GranTorino HB | Sofa",
  "sku": "5572*hi",
  "product_description": "The seat structure is in tubular metal...",
  "concept_and_design": "Designer Jean-Marie Massaud plays with...",
  "breadcrumbs": ["Home", "Products", "Products per line", "GranTorino HB | Sofa"],
  "designer": {
    "name": "JEAN-MARIE MASSAUD",
    "bio": "Born in Toulouse in 1966, Jean-Marie Massaud...",
    "image": "https://www.poltronafrau.com/.../jean-marie-massaud.jpg"
  },
  "images": {
    "hero_images": ["https://..."],
    "product_images": ["https://..."],
    "contextual_images": ["https://..."],
    "dimension_images": ["https://..."]
  },
  "downloads": [
    {
      "filename": "the-secret-garden-180x80-h63-table_obj.zip",
      "group": "OBJ",
      "text": "Download OBJ",
      "url": "/content/dam/ld/poltronafrau/products/.../the-secret-garden-180x80-h63-table_obj.zip"
    }
  ],
  "coverings_and_finishes": {
    "WOOD": {
      "TEAK": [
        {
          "color_caption": "TEAK",
          "color_name": "NATURAL",
          "color_url": "https://www.poltronafrau.com/.../naturale/0000027830.jpg"
        }
      ]
    },
    "FABRIC": {
      "Botè | A Category": [
        {
          "color_caption": "BOTÈ | A CATEGORY",
          "color_name": "AUBERGINE",
          "color_url": "https://www.poltronafrau.com/.../aubergine.jpg"
        }
      ]
    }
  }
}
```


### Key Technical Extraction Notes

1. **SKU Extraction**: Must read `data-product-sku` attribute from `div.product.product-configurator-aem` element - not available as visible text
2. **Breadcrumb Structure**: Has changed from "Products per category" to "Products per line" hierarchy

## Utilities

### download_html.py

A Python script that downloads rendered HTML content from Poltrona Frau product URLs using Selenium WebDriver.

**Purpose:** Downloads fully rendered HTML (after JavaScript execution) from URLs listed in `reference/tests/test_urls.txt` for testing and analysis purposes.

**Key Features:**
- Uses Selenium with Chrome WebDriver in headless mode
- Automatically manages ChromeDriver installation via webdriver-manager
- Waits for page content to fully load before capturing HTML
- Saves rendered HTML files to `reference/tests/` directory
- Handles multiple URLs sequentially with respectful delays

**Usage:**
```bash
uv run python download_html.py
```

**Dependencies:** 
- selenium
- webdriver-manager

**Output:** HTML files named after the product URL path (e.g., `grantorino-hb-sofa.html`)

### scraper.py

A comprehensive Python script that extracts structured product data from Poltrona Frau product pages using Selenium WebDriver.

**Purpose:** Extracts all available product data points from rendered HTML and outputs structured JSON files with organized data.

**Key Features:**
- Uses Selenium with Chrome WebDriver for dynamic content handling
- Comprehensive data extraction covering 11+ data points
- Intelligent fallback strategies for robust extraction
- Organized output structure with grouped related data
- Automatic JSON file generation with timestamped filenames
- Error handling and data validation

**Core Functions:**
- `extract_product_name()` - Product title extraction
- `extract_sku()` - SKU from data attributes
- `extract_designer()` - Designer name
- `extract_designer_bio()` - Designer biography from paneltext
- `extract_designer_image()` - Designer portrait image
- `extract_product_description()` - Technical product details
- `extract_concept_and_design()` - Collection concept
- `extract_breadcrumbs()` - Navigation hierarchy
- `extract_images_by_category()` - Organized image collections
- `extract_downloads()` - Download files and links

**Usage:**
```bash
# Scrape single URL with JSON output
uv run python -c "from scraper import scrape_product_from_url; scrape_product_from_url('URL')"

# Scrape without saving JSON
uv run python -c "from scraper import scrape_product_from_url; data = scrape_product_from_url('URL', save_to_json=False)"
```

**Dependencies:** 
- selenium
- webdriver-manager

**Output:** Timestamped JSON files in `reference/outcomes/` (e.g., `GranTorino-HB-Sofa_5572hi_20251104_000239.json`)

## Implementation Summary

### Current Status Overview

✅ **Complete (12/13 data points):**
- URL, Product Name, SKU, Designer, Breadcrumbs
- Product Description, Concept & Design, Designer Bio, Designer Image
- Organized Images (4 categories), Downloads
- Coverings & Finishes (3-layer grouped structure)

🔶 **Partial (1/13 data points):**
- Customization (configurator options - not yet implemented)

### Next Steps
1. **Implement Customization extraction** - analyze product configurator options

