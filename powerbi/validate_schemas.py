"""Validate documented PBIP/PBIR JSON schemas; not a substitute for Desktop testing."""
import json,urllib.request,warnings
from pathlib import Path
import jsonschema
warnings.filterwarnings('ignore',category=DeprecationWarning)
ROOT=Path(__file__).resolve().parent
CACHE=ROOT.parent/'artifacts/schema_cache';CACHE.mkdir(exist_ok=True)
def get(url):
    import hashlib
    # Microsoft's embedded schema declares a dotted $id although its published
    # filename uses a hyphen. Normalize this retrieval alias, not schema rules.
    url=url.replace('/schema.embedded.json','/schema-embedded.json')
    path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=40).read())
    schema=json.loads(path.read_text())
    schema['$id']=url
    return schema
def main():
    checked=[]
    for p in sorted(ROOT.rglob('*')):
        if p.suffix not in ['.json','.pbip','.pbir','.pbism']:continue
        data=json.loads(p.read_text())
        if '$schema' not in data:continue
        schema=get(data['$schema'])
        resolver=jsonschema.RefResolver(base_uri=data['$schema'],referrer=schema,handlers={'https':get})
        cls=jsonschema.validators.validator_for(schema)
        errors=list(cls(schema,resolver=resolver).iter_errors(data))
        if errors:raise ValueError(f'{p}: '+ '; '.join(e.message for e in errors))
        checked.append(str(p.relative_to(ROOT)))
    (ROOT.parent/'artifacts/powerbi_schema_validation.json').write_text(json.dumps({'validated_files':checked,
      'count':len(checked),'desktop_rendered':False,'pbix_created':False},indent=2))
    print(f'{len(checked)} documented JSON schemas passed. No Desktop rendering or PBIX export performed.')
if __name__=='__main__':main()
