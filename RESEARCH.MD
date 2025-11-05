# Poltrona Frau Product Page Scraping Analysis

This document outlines the findings and recommended approaches for scraping product data from a Poltrona Frau product page.

**URL Analyzed:** `https://www.poltronafrau.com/ww/en/products/grantorino-hb-sofa.html`

---

## Data Point Analysis

### SKU
- **Location:** The SKU is not reliably found as visible text. It is located in the `data-product-sku` attribute of a `div` element that wraps the product configurator.
- **Example HTML:** 
  ```html
  <div class="product product-configurator-aem aem-Grid aem-Grid--12" data-product-sku="5572*hi">
  ```
- **Approach:** Use a script to read the value of the `data-product-sku` attribute directly from the DOM. Standard text scraping will fail.

### Breadcrumbs
- **Location:** Found within a `<nav>` element with the `aria-label="Breadcrumb"`.
- **Update:** The site's breadcrumb structure has changed. The analyzed page uses a "Products per line" hierarchy, which is different from the "Products per category" structure in the reference JSON. The scraper logic must be updated to reflect this new structure.

### Coverings and Finishes ✅ IMPLEMENTED

- **Status:** ✅ Complete - 3-layer grouped structure implemented
- **Location:** Content is lazy-loaded from separate HTML files specified in `data-include` attributes within the "Coverings and finishes" tab
- **Implementation Method:** 
  1. Click "Coverings and finishes" tab to activate it
  2. Extract `data-include` URL from active tab panel elements
  3. Fetch separate HTML file via HTTP request
  4. Parse with BeautifulSoup to extract material types, categories, and individual finishes
- **Data Structure:** 3-layer hierarchy organized as:
  ```
  material_type (WOOD, FABRIC, LEATHER, METAL) >
    category (TEAK, Botè | A Category, etc.) >
      individual_finishes ([{color_caption, color_name, color_url}])
  ```
- **Example HTML Sources:**
  - Tab element: `<li role="tab" id="0-tab">WOOD</li>`
  - Panel content: `<div id="0" class="cmp-tabs__tabpanel">`
  - Accordion headers: `<h3 class="cmp-accordion__header"><span class="cmp-accordion__title">TEAK</span></h3>`
  - Individual items: `<div class="finishes__grid-cell">` with image and text components
  - Color caption: `<span class="cmp-image__title">TEAK</span>`
  - Color name: `<div class="finishes__grid-cell-text"><div class="cmp-text">NATURAL</div></div>`
- **Output Fields:**
  - `color_caption`: Material/finish type (e.g., "TEAK", "BOTÈ | A CATEGORY")
  - `color_name`: Specific color/finish name (e.g., "NATURAL", "AUBERGINE")
  - `color_url`: Full URL to finish image

### Customization Options

- **Location:** The customization options, including coatings and finishes, are available in the `data-multiple-coatings` attribute of the main product `div`. This attribute contains a JSON object with detailed information about each customization.
- **Status:** 🔶 Not yet implemented - requires configurator analysis
- **Example HTML:**
  ```html
  <div class="product product-configurator-aem aem-Grid aem-Grid--12" data-product-sku="5572*hi" data-product-url-key="grantorino-hb-sofa" data-ld-datalayer="{&#34;brand&#34;:&#34;poltronafrau&#34;,&#34;currency&#34;:&#34;EUR&#34;,&#34;item_id&#34;:&#34;5572*hi&#34;,&#34;item_name&#34;:&#34;GranTorino HB | Sofa&#34;,&#34;price&#34;:&#34;10260.00&#34;,&#34;item_category&#34;:&#34;Products|Armchairs and sofas&#34;,&#34;item_category2&#34;:&#34;Alcove seating&#34;}" data-rendering="2d" data-one-image="true" data-multiple-coatings='{"coating1":{"option_id":"4084","finishes":{"0000001680-0000001690":{"parents":"","title":"0000001680-0000001690","uid":"Y3VzdG9tLW9wdGlvbi80MDg0LzgwODgzNA==","option_type_id":"808834","parent":"RE-Saddle","image":"/content/dam/ld/poltronafrau/finishes/leather/pelle-frau-saddle/0000001690.jpg/jcr:content/renditions/cq5dam.thumbnail.{width}.{height}.jpg","name":"RE-SADDLE","description":"AVOCADO"}}}}'>
  ```
- **Approach:**
  1.  Select the `div.product` element.
  2.  Get the value of the `data-multiple-coatings` attribute.
  3.  Parse the value as a JSON object.
  4.  This object contains the customization data, which can then be processed as needed. This is a more direct and reliable way to get this data than simulating user interactions.

## Summary of Approach Updates

- **Static vs. Dynamic Scraping:** A simple static scrape of the initial HTML is insufficient. Key data points like the SKU and customization options require a more advanced approach.
- **Attribute Scraping:** Important data may be stored in `data-*` attributes, which are not part of the visible text.
- **Interactive Scraping:** Dynamic components, like the product configurator, must be interacted with (e.g., via clicks) to reveal all necessary data for scraping.

## Implementation Status & Technical Notes

### ✅ Completed Data Points (12/13)
1. **URL** - Direct from scraper input
2. **Product Name** - `h1.cmp-producthero__productName span`
3. **SKU** - `div.product.product-configurator-aem[data-product-sku]` attribute
4. **Product Description** - `div.productcontents .cmp-text p`
5. **Concept and Design** - Meta description tags
6. **Breadcrumbs** - JSON-LD structured data + HTML fallback
7. **Designer Name** - `h3.cmp-producthero__productDesigner`
8. **Designer Bio** - `div.text.paneltext p`
9. **Designer Image** - Images with "designer" or designer name in URL
10. **Images (4 categories)** - Organized by folder structure (hero, product, contextual, dimension)
11. **Downloads** - JavaScript extraction from `#professionals[data-download-track-api-url]`
12. **Coverings & Finishes** - 3-layer grouped structure from lazy-loaded HTML

### 🔶 Remaining Data Point (1/13)
- **Customization** - Product configurator options from `data-multiple-coatings` attribute

### Key Technical Implementation Details

#### Coverings & Finishes Extraction Process
1. **Tab Activation**: Click "Coverings and finishes" tab using JavaScript
2. **URL Discovery**: Extract `data-include` attribute from active tab panel
3. **Content Fetching**: HTTP request to separate HTML file (e.g., `.../finishes.lazyfinishes.html`)
4. **Parsing Strategy**: BeautifulSoup extraction with 3-layer hierarchy:
   - Material types from `<ol role="tablist">` tabs
   - Categories from accordion headers `<h3 class="cmp-accordion__header">`
   - Individual finishes from `<div class="finishes__grid-cell">` containers
5. **Data Structure**: Grouped as `{material_type: {category: [finishes_array]}}`

#### Selenium WebDriver Optimizations
- Headless Chrome mode for performance
- JavaScript execution for dynamic content interaction
- WebDriverWait for content loading
- BeautifulSoup integration for complex HTML parsing
- URL joining for relative path resolution

#### Output Generation
- Timestamped JSON files in `reference/outcomes/`
- Cleaned filenames from product names and SKUs
- Full URL generation for all image and download links
- Comprehensive error handling and fallback strategies