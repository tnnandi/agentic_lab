import requests
from bs4 import BeautifulSoup
import json
import re
import time

def test_basic_url_access(url):
    """Test basic web scraping of a URL"""
    try:
        print(f"Testing basic access to: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content (excluding code blocks)
            text_content = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract code blocks separately
            code_blocks = []
            for code in soup.find_all(['code', 'pre']):
                code_blocks.append(code.get_text().strip())
            
            print(f"✅ Successfully accessed {url}")
            print(f"Text content length: {len(text_content)} characters")
            print(f"Found {len(code_blocks)} code blocks")
            return True, text_content, code_blocks
        else:
            print(f"❌ Failed to access {url} - Status code: {response.status_code}")
            return False, None, None
    except Exception as e:
        print(f"❌ Error accessing {url}: {e}")
        return False, None, None

def main():
    """Test accessing the quality control page content"""
    test_url = "https://www.sc-best-practices.org/preprocessing_visualization/quality_control.html"
    
    print("=" * 80)
    print("TESTING QUALITY CONTROL PAGE ACCESS")
    print("=" * 80)
    
    # Test basic web scraping of the main page
    print("\nTesting main quality control page...")
    success, text_content, code_blocks = test_basic_url_access(test_url)
    
    if success:
        print(f"\n📄 TEXT CONTENT:")
        print("=" * 80)
        print(text_content)
        print("=" * 80)
        
        print(f"\n💻 CODE BLOCKS ({len(code_blocks)} found):")
        print("=" * 80)
        for i, code in enumerate(code_blocks, 1):
            print(f"\n--- Code Block {i} ---")
            print(code)
            print("-" * 40)
        print("=" * 80)
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main() 