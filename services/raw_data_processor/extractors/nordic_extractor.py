import json
import re
 
 
def extract_cars_from_html(html: str) -> list[dict]:
    """Extract the raw list of car dicts from a single MercadoLibre HTML page.
    Pure function — HTML in, list of car dicts out. No IO."""
    match = re.search(
        r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return []
 
    raw = match.group(1).strip()
    parts = re.split(r'(?=_n\.)', raw)
    json_str = re.sub(r'^_n\.ctx\.r=', '', parts[1]).rstrip(';')
    data = json.loads(json_str)
 
    return data["appProps"]["pageProps"]["initialState"]["pagination"]["search_api"]["results"]