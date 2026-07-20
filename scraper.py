import feedparser
import time
import random
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
                        
        # Rasmlarni original kattaligida olish
        if image_url and 'ichef.bbci.co.uk' in image_url and '/240/' in image_url:
            image_url = image_url.replace('/240/', '/800/')
        elif image_url and 'ichef.bbci.co.uk' in image_url and '/480/' in image_url:
            image_url = image_url.replace('/480/', '/800/')
            
        # Bo'sh qolsa zaxira rasm qo'yamiz (Katta va sifatli)
        fallbacks = [
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=800&auto=format&fit=crop", # Stadion va koptok
            "https://images.unsplash.com/photo-1518605368461-1e1c25143a41?q=80&w=800&auto=format&fit=crop", # O'yin maydoni
            "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=800&auto=format&fit=crop", # Tomoshabinlar
            "https://images.unsplash.com/photo-1511886929837-354d827a426d?q=80&w=800&auto=format&fit=crop", # Koptok va darvoza
            "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=800&auto=format&fit=crop" # Maydon chimi
        ]
        if not image_url:
            image_url = random.choice(fallbacks)
        
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
