import requests
from bs4 import BeautifulSoup
import json
import re
import time

def test_huggingface_download(url):
    """Test downloading the actual file from HuggingFace"""
    try:
        print(f"Testing HuggingFace direct download: {url}")
        
        # Try to get the raw file content
        # HuggingFace raw URLs typically use this format
        raw_url = url.replace('/blob/', '/resolve/')
        print(f"Attempting raw URL: {raw_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(raw_url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Successfully downloaded raw content")
            print(f"Content length: {len(content)} characters")
            print(f"First 10000 characters: {content[:10000]}...")
            return True, content
        else:
            print(f"❌ Raw download failed, status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return False, None

def test_huggingface_api_v2(url):
    """Test HuggingFace API with different endpoint"""
    try:
        # Extract repo and file path from URL
        match = re.search(r'huggingface\.co/([^/]+)/([^/]+)/blob/([^/]+)/(.+)', url)
        if not match:
            print("❌ Could not parse HuggingFace URL format")
            return False, None
            
        username, repo, branch, file_path = match.groups()
        
        # Try different API endpoints
        api_endpoints = [
            f"https://huggingface.co/api/repos/{username}/{repo}/files/{file_path}?ref={branch}",
            f"https://huggingface.co/api/repos/{username}/{repo}/resolve/{file_path}?ref={branch}",
            f"https://huggingface.co/{username}/{repo}/resolve/{branch}/{file_path}"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for i, api_url in enumerate(api_endpoints, 1):
            print(f"Testing API endpoint {i}: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.text
                print(f"✅ Successfully accessed via API endpoint {i}")
                print(f"Content length: {len(content)} characters")
                print(f"First 10000 characters: {content[:10000]}...")
                return True, content
            else:
                print(f"❌ API endpoint {i} failed, status code: {response.status_code}")
        
        return False, None
    except Exception as e:
        print(f"❌ Error accessing HuggingFace API: {e}")
        return False, None

def test_selenium_approach(url):
    """Test using Selenium to handle JavaScript-rendered content"""
    try:
        print(f"Testing Selenium approach for: {url}")
        
        # This would require selenium installation
        # For now, just show the approach
        print("⚠️  Selenium approach would require:")
        print("   - pip install selenium")
        print("   - Download chromedriver")
        print("   - Handle JavaScript rendering")
        return False, None
    except Exception as e:
        print(f"❌ Selenium approach error: {e}")
        return False, None

def extract_download_link_from_html(html_content):
    """Extract download link from HuggingFace HTML page"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for download links or raw file links
        download_links = soup.find_all('a', href=True)
        
        for link in download_links:
            href = link.get('href')
            if href and ('raw' in href or 'resolve' in href or 'download' in href):
                print(f"Found potential download link: {href}")
                return href
        
        # Look for specific patterns in the page
        text_content = soup.get_text()
        if 'raw' in text_content or 'download' in text_content:
            print("Found raw/download references in page content")
            return None
            
        return None
    except Exception as e:
        print(f"❌ Error extracting download link: {e}")
        return None

def test_manual_download_link(url):
    """Test manually constructed download link"""
    try:
        # Try different URL patterns for HuggingFace
        base_url = "https://huggingface.co/ctheodoris/Geneformer/resolve/main/examples/tokenizing_scRNAseq_data.ipynb"
        print(f"Testing manual download link: {base_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Successfully downloaded via manual link")
            print(f"Content length: {len(content)} characters")
            print(f"First 10000 characters: {content[:10000]}...")
            return True, content
        else:
            print(f"❌ Manual download failed, status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error with manual download: {e}")
        return False, None

def main():
    """Test different methods to access the HuggingFace URL"""
    test_url = "https://huggingface.co/ctheodoris/Geneformer/blob/main/examples/tokenizing_scRNAseq_data.ipynb"
    
    print("=" * 60)
    print("TESTING IMPROVED URL ACCESS METHODS")
    print("=" * 60)
    
    # Test 1: Manual download link
    print("\n1. Testing manual download link...")
    success_manual, content_manual = test_manual_download_link(test_url)
    
    # Test 2: HuggingFace API v2
    print("\n2. Testing HuggingFace API v2...")
    success_api, content_api = test_huggingface_api_v2(test_url)
    
    # Test 3: Direct download
    print("\n3. Testing direct download...")
    success_download, content_download = test_huggingface_download(test_url)
    
    # Test 4: Selenium approach (info only)
    print("\n4. Testing Selenium approach...")
    test_selenium_approach(test_url)
    
    # Parse notebook content if we got any
    print("\n" + "=" * 60)
    print("PARSING RESULTS")
    print("=" * 60)
    
    content_to_parse = None
    if success_manual and content_manual:
        content_to_parse = content_manual
        print("\nUsing manual download content...")
    elif success_api and content_api:
        content_to_parse = content_api
        print("\nUsing API content...")
    elif success_download and content_download:
        content_to_parse = content_download
        print("\nUsing direct download content...")
    
    if content_to_parse:
        try:
            # Try to parse as JSON (Jupyter notebook format)
            notebook = json.loads(content_to_parse)
            print(f"✅ Successfully parsed as Jupyter notebook")
            print(f"Notebook has {len(notebook.get('cells', []))} cells")
            
            # Extract text from cells
            extracted_text = []
            for i, cell in enumerate(notebook.get('cells', [])):
                cell_type = cell.get('cell_type', '')
                source = cell.get('source', [])
                
                if isinstance(source, list):
                    text = ''.join(source)
                else:
                    text = str(source)
                
                if cell_type == 'markdown':
                    extracted_text.append(f"## Cell {i+1} (Markdown)\n{text}\n")
                elif cell_type == 'code':
                    extracted_text.append(f"## Cell {i+1} (Code)\n```python\n{text}\n```\n")
            
            final_content = '\n'.join(extracted_text)
            print(f"Extracted content length: {len(final_content)} characters")
            print(f"First 10000 characters:\n{final_content[:10000]}...")
            
        except json.JSONDecodeError:
            print("❌ Content is not valid JSON (not a Jupyter notebook)")
            print(f"Content preview: {content_to_parse[:10000]}...")
    else:
        print("\n❌ No content was successfully retrieved from any method")

if __name__ == "__main__":
    main() 