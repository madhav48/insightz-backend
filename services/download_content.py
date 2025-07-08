import requests
from bs4 import BeautifulSoup

def is_url_valid(url):
    try:
        response = requests.get(
            url,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"},
            verify=True
        )
        return response.status_code == 200
    except Exception:
        return False

def download_and_extract_text(url):
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Optionally, collapse multiple newlines
        text = "\n".join([line for line in text.splitlines() if line.strip()])
        return text
    except Exception as e:
        return f"Error downloading {url}: {str(e)}"
    


def load_documents(urls):
    if not urls:
        return []
    valid_urls = [url for url in urls if is_url_valid(url)]
    if not valid_urls:
        return []
    documents = []
    for url in valid_urls:
        content = download_and_extract_text(url)
        # documents.append({"url": url, "content": content})
        documents.append(content)
    return documents
