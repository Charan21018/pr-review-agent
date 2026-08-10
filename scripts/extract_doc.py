import re

with open('Designing an AI Pull-Request Review Agent.html', 'r', encoding='utf-8') as f:
    html = f.read()

sections = {
    'module_map': ('s-modulemap', 's-tigerplan'),
    'tiger_plan': ('s-tigerplan', 's-reuse'),
    'ingress_queue': ('s-ingress', 's-orchestrator'),
    'orchestrator': ('s-orchestrator', 's-tradeoff'),
    'specialists': ('s-specialists', 's-retrieval'),
    'retrieval': ('s-retrieval', 's-events'),
    'events': ('s-events', 's-fullsystem'),
}

for name, (start_id, end_id) in sections.items():
    pat = re.compile(r'id="' + re.escape(start_id) + r'"(.*?)id="' + re.escape(end_id) + r'"', re.DOTALL)
    m = pat.search(html)
    if m:
        text = re.sub(r'<[^>]+>', ' ', m.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        print(f"\n{'='*60}")
        print(f"SECTION: {name}")
        print('='*60)
        print(text[:3000].encode('ascii', 'replace').decode('ascii'))
    else:
        print(f"\nSECTION NOT FOUND: {name}")
