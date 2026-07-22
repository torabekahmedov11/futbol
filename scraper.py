import feedparser
import time
import random
from bs4 import BeautifulSoup

FALLBACK_FOOTBALL_IMAGES = [
    "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518605368461-1e1c25143a41?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511886929837-354d827a426d?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560272564-6694e9340f1a?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1543326727-cf6c39e8f84c?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1575361204480-aadea25e6e68?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1529900748604-07564a03e7a6?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1551958219-acbc608c6377?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517466787929-bc90951d0974?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518091043644-c1d4457512c6?q=80&w=800&auto=format&fit=crop"
]

_recent_images = []

def get_unique_fallback_image():
    global _recent_images
    available = [img for img in FALLBACK_FOOTBALL_IMAGES if img not in _recent_images]
    if not available:
        _recent_images = []
        available = FALLBACK_FOOTBALL_IMAGES
    choice = random.choice(available)
    _recent_images.append(choice)
    if len(_recent_images) > 8:
        _recent_images.pop(0)
    return choice

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
            
        post_time = time.time()
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            post_time = time.mktime(entry.published_parsed)
            now_time = time.time()
            if (now_time - post_time) > (6 * 3600):  # Faqat oxirgi 6 soatdagi YANGI xabarlar
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
                        
        # Rasmlarni original kattaligida olish
        if image_url and 'ichef.bbci.co.uk' in image_url and '/240/' in image_url:
            image_url = image_url.replace('/240/', '/800/')
        elif image_url and 'ichef.bbci.co.uk' in image_url and '/480/' in image_url:
            image_url = image_url.replace('/480/', '/800/')
            
        if not image_url:
            image_url = get_unique_fallback_image()
        
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
            "type": "news",
            "created_at": post_time
        })
        
    return new_posts
