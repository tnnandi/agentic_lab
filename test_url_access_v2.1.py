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
            
            text_content = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = ' '.join(chunk for chunk in chunks if chunk)
            
            print(f"✅ Successfully accessed {url}")
            print(f"Content length: {len(text_content)} characters")
            print(f"First 1000 characters: {text_content[:1000]}...")
            return True, text_content
        else:
            print(f"❌ Failed to access {url} - Status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Error accessing {url}: {e}")
        return False, None

def main():
    """Test accessing the quality control page content"""
    test_url = "https://www.sc-best-practices.org/preprocessing_visualization/quality_control.html"
    
    print("=" * 80)
    print("TESTING QUALITY CONTROL PAGE ACCESS")
    print("=" * 80)
    
    # Test basic web scraping of the main page
    print("\nTesting main quality control page...")
    success, content = test_basic_url_access(test_url)
    
    if success:
        print(f"\n📄 Full page content:")
        print("=" * 80)
        print(content)
        print("=" * 80)
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main() 