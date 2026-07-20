import feedparser
import time
from bs4 import BeautifulSoup

def scrape_telegram_channel(rss_url, last_id):
    """
    Saytning RSS Feed zanjiridan postlarni o'qiydi.
    """
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"Scraper error (RSS o'qishda): {e}")
        return []

    new_posts = []
    entries = reversed(feed.entries)
    
    for entry in entries:
        post_id = entry.get('link', '') or entry.get('id', '')
        if not post_id:
            continue
            
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            post_time = time.mktime(entry.published_parsed)
            now_time = time.time()
            if (now_time - post_time) > (24 * 3600):
                continue
        
        text = entry.get('title', '') + "\n\n"
        content_html = entry.get('summary', '') or entry.get('description', '')
        if 'content' in entry and len(entry.content) > 0:
            content_html = entry.content[0].value
            
        soup = BeautifulSoup(content_html, 'html.parser')
        
        image_url = None
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            image_url = img_tag.get('src')
            
        if not image_url:
            if 'media_content' in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get('url')
            elif 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                image_url = entry.media_thumbnail[0].get('url')
            elif getattr(entry, 'enclosures', None):
                for enc in entry.enclosures:
                    if 'image' in getattr(enc, 'type', '') or 'image' in enc.get('type', ''):
                        image_url = enc.get('href')
                        break
        
        clean_summary = soup.get_text('\n', strip=True)
        if clean_summary and clean_summary != entry.get('title', ''):
            text += clean_summary
            
        title_lower = entry.get('title', '').lower()
        link_lower = post_id.lower()
        
        ad_keywords = ['deal', 'sale', 'sponsor', 'promoted', 'amazon', 'aliexpress', 'discount', '% off', 'coupon', 'woot']
        is_ad = False
        for kw in ad_keywords:
            if kw in title_lower or kw in link_lower:
                is_ad = True
                break
                
        if is_ad:
            continue
            
        new_posts.append({
            "id": post_id,
            "text": text,
            "image": image_url,
            "video": None,
            "type": "news"
        })
        
    return new_posts
