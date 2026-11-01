"""
Validates Power BI PBIP/PBIR JSON definitions against Microsoft Fabric schemas.
"""

import json
import urllib.request
import warnings
from pathlib import Path
import jsonschema

warnings.filterwarnings('ignore', category=DeprecationWarning)
ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parent / 'artifacts/schema_cache'
CACHE.mkdir(exist_ok=True)


def get_schema(url: str) -> dict:
    import hashlib
    # Normalize retrieval alias
    url_normalized = url.replace('/schema.embedded.json', '/schema-embedded.json')
    cached_path = CACHE / (hashlib.sha256(url_normalized.encode()).hexdigest() + '.json')
    if not cached_path.exists():
        cached_path.write_bytes(urllib.request.urlopen(url_normalized, timeout=40).read())
    schema = json.loads(cached_path.read_text())
    schema['$id'] = url
    return schema


def main():
    checked = []
    for p in sorted(ROOT.rglob('*')):
        if p.suffix not in ['.json', '.pbip', '.pbir', '.pbism']:
            continue
        data = json.loads(p.read_text())
        if '$schema' not in data:
            continue
        schema = get_schema(data['$schema'])
        resolver = jsonschema.RefResolver(base_uri=data['$schema'], referrer=schema, handlers={'https': get_schema})
        cls = jsonschema.validators.validator_for(schema)
        errors = list(cls(schema, resolver=resolver).iter_errors(data))
        if errors:
            raise ValueError(f'{p}: ' + '; '.join(e.message for e in errors))
        checked.append(str(p.relative_to(ROOT)))

    print(f'Successfully validated {len(checked)} Power BI schema files.')


if __name__ == '__main__':
    main()
