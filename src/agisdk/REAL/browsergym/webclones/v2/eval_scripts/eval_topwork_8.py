import sys, json

def deep_get(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Heuristic to determine if a job is data-related
# Strategy:
# - Prefer strong signals: category/subcategory contains 'data'
# - Then look for keywords in title/description indicating analytics/analysis/ML/statistics/visualization
# - Finally, look for known data-science skills/libraries; avoid overly broad terms like 'SQL' alone to reduce false positives

def is_data_related(job):
    if not isinstance(job, dict):
        return False
    title = (job.get('title') or '').lower()
    desc = (job.get('description') or '').lower()
    category = (job.get('category') or '').lower()
    subcat = (job.get('subcategory') or '').lower()
    skills = job.get('skills') or []
    skills_text = ' '.join([str(s).lower() for s in skills if s is not None])

    # Strong category/subcategory signal
    if 'data' in category or 'data' in subcat:
        return True

    # Title keywords
    title_kw = ['data', 'analytics', 'analysis', 'analyst', 'machine learning', 'ml', 'data science']
    if any(kw in title for kw in title_kw):
        return True

    # Description keywords (require presence of 'data' plus another specific analytic term to avoid generic matches)
    desc_secondary = ['analysis', 'analytics', 'visualization', 'visualisation', 'machine learning', 'statistical', 'statistics', 'modeling', 'modelling']
    if 'data' in desc and any(kw in desc for kw in desc_secondary):
        return True

    # Skills indicating data work
    data_skills = [
        'pandas','numpy','matplotlib','seaborn','scikit','sklearn','scikit-learn',
        'tensorflow','pytorch','keras','hadoop','spark','tableau','power bi','powerbi',
        'plotly','bokeh','d3','etl','data engineering','data science','ml','machine learning'
    ]
    if any(ds in skills_text for ds in data_skills):
        return True

    return False


def main():
    # Load JSON state from file path provided as first argument
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Navigate to removed job posts list
    removed_posts = deep_get(data, ['initialfinaldiff', 'added', 'jobs', 'removedJobPosts'], [])
    if removed_posts is None:
        removed_posts = []

    # Determine success: at least one removed post is data-related
    success = False
    if isinstance(removed_posts, list) and len(removed_posts) > 0:
        for job in removed_posts:
            if is_data_related(job):
                success = True
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
