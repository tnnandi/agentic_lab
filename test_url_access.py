import requests
from bs4 import BeautifulSoup
import json
import re

def test_basic_url_access(url):
    """Test basic web scraping of a URL"""
    try:
        print(f"Testing basic access to: {url}")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text()
            print(f"✅ Successfully accessed {url}")
            print(f"Content length: {len(text_content)} characters")
            print(f"First 500 characters: {text_content[:500]}...")
            return True, text_content
        else:
            print(f"❌ Failed to access {url}, status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error accessing {url}: {e}")
        return False, None

def test_huggingface_api(url):
    """Test accessing HuggingFace content via API"""
    try:
        # Extract repo and file path from URL
        # URL format: https://huggingface.co/username/repo/blob/main/path/to/file
        match = re.search(r'huggingface\.co/([^/]+)/([^/]+)/blob/([^/]+)/(.+)', url)
        if not match:
            print("❌ Could not parse HuggingFace URL format")
            return False, None
            
        username, repo, branch, file_path = match.groups()
        
        # Use HuggingFace API
        api_url = f"https://huggingface.co/api/repos/{username}/{repo}/files/{file_path}?ref={branch}"
        print(f"Testing HuggingFace API: {api_url}")
        
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Successfully accessed via API")
            print(f"Content length: {len(content)} characters")
            print(f"First 10000 characters: {content[:10000]}...")
            return True, content
        else:
            print(f"❌ API failed, status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error accessing HuggingFace API: {e}")
        return False, None

def test_github_raw(url):
    """Test accessing GitHub raw content"""
    try:
        # Convert GitHub blob URL to raw URL
        raw_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        print(f"Testing GitHub raw access: {raw_url}")
        
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Successfully accessed raw content")
            print(f"Content length: {len(content)} characters")
            print(f"First 10000 characters: {content[:10000]}...")
            return True, content
        else:
            print(f"❌ Raw access failed, status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error accessing raw content: {e}")
        return False, None

def parse_jupyter_notebook(content):
    """Parse Jupyter notebook content"""
    try:
        notebook = json.loads(content)
        cells = notebook.get('cells', [])
        
        extracted_text = []
        for cell in cells:
            cell_type = cell.get('cell_type', '')
            if cell_type == 'markdown':
                # Get markdown content
                source = cell.get('source', [])
                if isinstance(source, list):
                    text = ''.join(source)
                else:
                    text = str(source)
                extracted_text.append(f"## Markdown Cell\n{text}\n")
            elif cell_type == 'code':
                # Get code content
                source = cell.get('source', [])
                if isinstance(source, list):
                    code = ''.join(source)
                else:
                    code = str(source)
                extracted_text.append(f"## Code Cell\n```python\n{code}\n```\n")
        
        return '\n'.join(extracted_text)
    except Exception as e:
        print(f"❌ Error parsing notebook: {e}")
        return content

def main():
    """Test different methods to access the HuggingFace URL"""
    test_url = "https://huggingface.co/ctheodoris/Geneformer/blob/main/examples/tokenizing_scRNAseq_data.ipynb"
    
    print("=" * 60)
    print("TESTING URL ACCESS METHODS")
    print("=" * 60)
    
    # Test 1: Basic web scraping
    print("\n1. Testing basic web scraping...")
    success, content = test_basic_url_access(test_url)
    
    # Test 2: HuggingFace API
    print("\n2. Testing HuggingFace API...")
    success_api, content_api = test_huggingface_api(test_url)
    
    # Test 3: GitHub raw (if it's a GitHub-style URL)
    print("\n3. Testing GitHub raw access...")
    success_raw, content_raw = test_github_raw(test_url)
    
    # Parse notebook content if we got any
    print("\n" + "=" * 60)
    print("PARSING RESULTS")
    print("=" * 60)
    
    if success_api and content_api:
        print("\nParsing HuggingFace API content as notebook...")
        parsed_content = parse_jupyter_notebook(content_api)
        print(f"Parsed content length: {len(parsed_content)} characters")
        print(f"First 10000 characters of parsed content:\n{parsed_content[:10000]}...")
    
    elif success_raw and content_raw:
        print("\nParsing raw content as notebook...")
        parsed_content = parse_jupyter_notebook(content_raw)
        print(f"Parsed content length: {len(parsed_content)} characters")
        print(f"First 10000 characters of parsed content:\n{parsed_content[:10000]}...")
    
    elif success and content:
        print("\nParsing basic scraped content...")
        print(f"Basic content length: {len(content)} characters")
        print(f"First 10000 characters:\n{content[:10000]}...")
    
    else:
        print("\n❌ No content was successfully retrieved from any method")

if __name__ == "__main__":
    main() 