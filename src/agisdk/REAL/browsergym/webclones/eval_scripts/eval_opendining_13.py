import json, sys, re

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Positive sentiment check focused on food-related praise
POSITIVE_KEYWORDS = [
    'amazing', 'excellent', 'great', 'fantastic', 'awesome', 'delicious', 'tasty',
    'wonderful', 'incredible', 'so good', 'very good', 'really good', 'love', 'loved'
]

def is_positive_food_text(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    t = text.strip().lower()
    if 'food' not in t:
        return False
    return any(k in t for k in POSITIVE_KEYWORDS)

# Ratings must all be 5
REQUIRED_RATING_FIELDS = ['Overall', 'Food', 'Service', 'Ambience']

def is_five_star(review: dict) -> bool:
    for key in REQUIRED_RATING_FIELDS:
        val = review.get(key)
        try:
            if int(val) != 5:
                return False
        except Exception:
            return False
    return True

# Extract reviews dict from typical locations

def extract_reviews(data: dict):
    reviews = None
    try:
        reviews = data.get('initialfinaldiff', {}).get('added', {}).get('review', {}).get('reviews')
    except Exception:
        reviews = None
    if not reviews:
        try:
            reviews = data.get('initialfinaldiff', {}).get('updated', {}).get('review', {}).get('reviews')
        except Exception:
            reviews = None
    # Normalize to list of review dicts
    out = []
    if isinstance(reviews, dict):
        for _, v in reviews.items():
            if isinstance(v, dict):
                out.append(v)
    elif isinstance(reviews, list):
        out = [r for r in reviews if isinstance(r, dict)]
    return out


def main():
    # Strategy:
    # - Verify there are 5-star, positive food-text reviews for the target restaurants inferred from the success example.
    # - Ensure no reviews exist for other restaurant IDs (to avoid wrong-restaurant mistakes) and all required IDs are covered.
    path = sys.argv[1]
    data = load_json(path)

    reviews = extract_reviews(data)
    if not reviews:
        print('FAILURE')
        return

    # Inferred correct restaurant IDs from the successful training state
    REQUIRED_IDS = {
        '81c94d5b-47b1-4d3f-bc48-e2cbebbc2d0f',
        '72eabc38-0f6c-4f56-bf2f-09b9b8e04f7c'
    }

    found_valid = {rid: False for rid in REQUIRED_IDS}
    extraneous_found = False
    invalid_in_required = False

    for r in reviews:
        rid = r.get('restaurantId')
        text = r.get('text')
        five_star = is_five_star(r)
        positive = is_positive_food_text(text)

        if rid in REQUIRED_IDS:
            if five_star and positive:
                found_valid[rid] = True
            else:
                # A review exists for a required restaurant but doesn't meet criteria
                invalid_in_required = True
        else:
            # Any review for a non-required restaurant indicates wrong restaurant was reviewed
            extraneous_found = True

    # Success only if all required restaurants have at least one valid review,
    # there are no extraneous restaurants reviewed, and no invalid reviews for required ones
    if all(found_valid.values()) and not extraneous_found and not invalid_in_required:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()