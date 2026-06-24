import csv
import re
import string
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Common English stop words to filter out from frequency-based keywords
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "this", "that", "was",
    "are", "be", "as", "have", "has", "had", "not", "we", "you", "he",
    "she", "they", "i", "my", "your", "our", "their", "will", "can", "do",
    "if", "so", "up", "out", "about", "more", "also", "than", "then",
    "which", "when", "there", "been", "were", "what", "all", "one", "any",
}


def scrape_website(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup


def extract_keywords(soup):
    keywords = []

    # 1. Meta keywords tag
    meta_kw = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
    if meta_kw and meta_kw.get("content"):
        for kw in meta_kw["content"].split(","):
            kw = kw.strip()
            if kw:
                keywords.append({"keyword": kw, "source": "meta"})

    # 2. Meta description tag (treat whole value as a keyword phrase)
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_desc and meta_desc.get("content"):
        keywords.append({"keyword": meta_desc["content"].strip(), "source": "meta_description"})

    # 3. Open Graph keywords / description
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        keywords.append({"keyword": og_desc["content"].strip(), "source": "og_description"})

    # 4. Frequency-based keywords from visible page text (top 20)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    words = text.lower().translate(str.maketrans("", "", string.punctuation)).split()
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    for word, count in Counter(filtered).most_common(20):
        keywords.append({"keyword": word, "source": f"frequency (count={count})"})

    return keywords


def extract_data(soup, base_url):
    title = soup.title.get_text(strip=True) if soup.title else "N/A"

    headings = [
        {"type": h.name.upper(), "text": h.get_text(strip=True)}
        for h in soup.find_all(["h1", "h2", "h3"])
    ]

    links = [
        {"text": a.get_text(strip=True), "href": urljoin(base_url, a.get("href"))}
        for a in soup.find_all("a", href=True)
    ]

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    ]

    keywords = extract_keywords(soup)

    return title, headings, links, paragraphs, keywords


def save_to_csv(title, headings, links, paragraphs, keywords):
    with open("headings.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["type", "text"])
        writer.writeheader()
        writer.writerows(headings)

    with open("links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "href"])
        writer.writeheader()
        writer.writerows(links)

    with open("paragraphs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["paragraph"])
        writer.writerows([[p] for p in paragraphs])

    with open("keywords.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "source"])
        writer.writeheader()
        writer.writerows(keywords)

    with open("summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "value"])
        writer.writerow(["title", title])
        writer.writerow(["total_headings", len(headings)])
        writer.writerow(["total_links", len(links)])
        writer.writerow(["total_paragraphs", len(paragraphs)])
        writer.writerow(["total_keywords", len(keywords)])


def main():
    url = "https://example.com"  # Replace with your target URL
    print(f"Scraping: {url}\n")

    soup = scrape_website(url)
    title, headings, links, paragraphs, keywords = extract_data(soup, url)
    save_to_csv(title, headings, links, paragraphs, keywords)

    print("Done! Saved 5 CSV files:")
    print("  summary.csv    — page title and counts")
    print("  headings.csv   — all h1/h2/h3 headings")
    print("  links.csv      — all links with href")
    print("  paragraphs.csv — all paragraph text")
    print("  keywords.csv   — meta keywords + top frequency words")


if __name__ == "__main__":
    main()
