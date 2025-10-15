import sys, json

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# Extract saved freelancer IDs from both 'added' and 'updated' sections

def get_saved_ids(state):
    saved_ids = set()
    if not isinstance(state, dict):
        return saved_ids
    for section in ("added", "updated"):
        sec = state.get(section, {})
        saved = sec.get("saved", {}) if isinstance(sec, dict) else {}
        ids = saved.get("savedFreelancerIds") if isinstance(saved, dict) else None
        if isinstance(ids, dict):
            for v in ids.values():
                if isinstance(v, str) and v.strip():
                    saved_ids.add(v.strip())
        elif isinstance(ids, list):
            for v in ids:
                if isinstance(v, str) and v.strip():
                    saved_ids.add(v.strip())
    return saved_ids

# Collect cover letters for each freelancer across all job applications

def get_freelancer_coverletters(state):
    fl_to_texts = {}
    if not isinstance(state, dict):
        return fl_to_texts
    for section in ("added", "updated"):
        sec = state.get(section, {})
        jobs_container = sec.get("jobs", {}) if isinstance(sec, dict) else {}
        jobs = jobs_container.get("jobs", {}) if isinstance(jobs_container, dict) else {}
        if isinstance(jobs, dict):
            for job in jobs.values():
                if not isinstance(job, dict):
                    continue
                apps = job.get("applications", [])
                if isinstance(apps, list):
                    for app in apps:
                        if not isinstance(app, dict):
                            continue
                        fid = app.get("freelancerId")
                        cl = app.get("coverLetter", "")
                        if isinstance(fid, str):
                            fl_to_texts.setdefault(fid, []).append(cl if isinstance(cl, str) else "")
    return fl_to_texts

# Determine if a text indicates backend capabilities via strong keyword matching

def text_is_backend(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    t = text.lower()
    # Strong backend indicators (avoid overly generic ones to reduce false positives)
    keywords = [
        "backend", "back-end", "server-side", "server ", " servers", "microservice", "microservices",
        "node.js", "nodejs", " node ", "express", "nestjs",
        "django", "flask", "fastapi", "rails", "ruby on rails",
        "laravel", "php backend", " php ",
        ".net", "c#", "spring", "spring boot", "java backend", " kotlin server",
        "golang", " go ", "go-lang", "grpc",
        "rest api", "restful", "graphql", " api", " api.", " apis", "endpoint",
        "postgres", "postgresql", "mysql", "mongodb", "redis", "sqlite",
        "kafka", "rabbitmq",
        "docker", "kubernetes", "container", "containers",
        "lambda", "cloud function", "cloud functions",
    ]
    # Simple contains check for any keyword
    return any(k in t for k in keywords)


def any_saved_backend(state):
    saved_ids = get_saved_ids(state)
    if not saved_ids:
        return False
    fl_coverletters = get_freelancer_coverletters(state)
    for fid in saved_ids:
        texts = fl_coverletters.get(fid, [])
        combined = " \n ".join([t for t in texts if isinstance(t, str)])
        if text_is_backend(combined):
            return True
    return False


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    data = load_json(path)
    if not isinstance(data, dict):
        print("FAILURE")
        return
    state = data.get("initialfinaldiff") if isinstance(data, dict) else None
    if not isinstance(state, dict):
        print("FAILURE")
        return
    result = any_saved_backend(state)
    print("SUCCESS" if result else "FAILURE")

if __name__ == "__main__":
    main()
