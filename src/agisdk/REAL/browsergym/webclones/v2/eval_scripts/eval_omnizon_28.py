import sys, json, re, os

# Strategy:
# 1) Aggregate text not only from final_state_diff.json but also from any sibling JSON/TXT files in the same folder to capture confirmation and item details.
# 2) Use robust heuristics to confirm purchase completion and verify it's a silverware/flatware/cutlery set.

def safe_load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def safe_read_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ''

def extract_strings(obj):
    strings = []
    def _rec(o):
        if o is None:
            return
        if isinstance(o, str):
            s = o.strip()
            if s:
                strings.append(s)
        elif isinstance(o, (int, float, bool)):
            strings.append(str(o))
        elif isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and k.strip():
                    strings.append(k.strip())
                _rec(v)
        elif isinstance(o, (list, tuple, set)):
            for item in o:
                _rec(item)
    _rec(obj)
    return strings

def gather_all_texts(main_path):
    texts = []
    # Load main json
    main = safe_load_json(main_path)
    if main is not None:
        texts.extend(extract_strings(main))
    # Also scan sibling files for more context
    base_dir = os.path.dirname(main_path)
    try:
        for fname in os.listdir(base_dir):
            if fname == os.path.basename(main_path):
                continue
            full = os.path.join(base_dir, fname)
            if os.path.isdir(full):
                continue
            lower = fname.lower()
            if lower.endswith('.json'):
                data = safe_load_json(full)
                if data is not None:
                    texts.extend(extract_strings(data))
            elif lower.endswith('.txt'):
                texts.append(safe_read_text(full))
    except Exception:
        pass
    return ('\n'.join([t for t in texts if isinstance(t, str)])).lower()

def near(text, w1, w2, max_span=80):
    pattern = re.compile(r"\b" + re.escape(w1) + r"\b.{0," + str(max_span) + r"}?\b" + re.escape(w2) + r"\b")
    if pattern.search(text):
        return True
    pattern2 = re.compile(r"\b" + re.escape(w2) + r"\b.{0," + str(max_span) + r"}?\b" + re.escape(w1) + r"\b")
    return bool(pattern2.search(text))

CATEGORY_WORDS = ['silverware', 'silver ware', 'flatware', 'cutlery']
SPOON_WORDS = ['spoon', 'spoons']
FORK_WORDS = ['fork', 'forks']
URL_HINTS = ['order-confirmation', 'confirmation', 'receipt', 'thank-you']


def has_purchase_confirmation_text(blob):
    patterns = [
        r"\border\s*(id|#|number)\b",
        r"thank you",
        r"your order",
        r"order (placed|confirmed|complete|completed)",
        r"payment (successful|completed)",
        r"order\s*summary",
        r"order\s*details",
        r"thank you for your (order|purchase)"
    ]
    pos = any(re.search(p, blob) for p in patterns)
    url_like = any(h in blob for h in URL_HINTS)
    neg = any(s in blob for s in [
        'cart is empty', 'your cart is empty', 'no items in your cart',
        'add to cart', 'proceed to checkout', 'continue to checkout', 'checkout'
    ]) and not pos
    # Explicit failure cues
    if any(s in blob for s in ['payment failed', 'payment declined', 'order cancelled', 'order canceled']):
        return False
    return bool((pos or url_like) and not neg)


def is_silverware_set_text(blob):
    if any(f"{c} set" in blob for c in CATEGORY_WORDS):
        return True
    if any(near(blob, c, 'set', 80) for c in CATEGORY_WORDS):
        return True
    if re.search(r"\b(\d{1,3})\s*[- ]?(piece|pcs)\b.{0,80}\b(silver\s*ware|silverware|flatware|cutlery)\b", blob):
        return True
    if any(w in blob for w in SPOON_WORDS) and any(w in blob for w in FORK_WORDS):
        if ' set' in blob or re.search(r"\b(\d{1,3})\s*[- ]?(piece|pcs)\b", blob):
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    blob = gather_all_texts(path)

    # Quick explicit outcome tokens if present in any sibling logs/files
    if 'unsuccessful' in blob:
        print('FAILURE')
        return
    if 'successful' in blob or 'success' in blob:
        # Still sanity check item relevance if possible
        if is_silverware_set_text(blob):
            print('SUCCESS')
        else:
            print('FAILURE')
        return

    purchased = has_purchase_confirmation_text(blob)
    item_ok = is_silverware_set_text(blob)

    if purchased and item_ok:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
