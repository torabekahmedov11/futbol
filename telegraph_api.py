from telegraph import Telegraph

_telegraph = Telegraph()
_telegraph.create_account(short_name='Batafsil', author_name='Kanal Qo\'llanmasi')

def create_telegraph_page(title, html_content):
    """
    Kiritilgan HTML matndan Telegraph maqolasi yaratadi va ULR'ni qaytaradi.
    """
    try:
        html_content = html_content.replace('\n', '<br>')
        response = _telegraph.create_page(
            title=title,
            html_content=html_content
        )
        return response['url']
    except Exception as e:
        print(f"Telegraph sahifa yaratishda xato: {e}")
        return None
