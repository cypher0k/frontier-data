import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(data):
 assert data.get('schemaVersion')==1 and data.get('generatedAt'),'Publication metadata missing'
 ids=set();names=set()
 for t in data['terms']:
  assert re.fullmatch('[a-z0-9][a-z0-9-]{0,119}',t['id']) and t['id'] not in ids,'Duplicate/invalid ID'
  name=re.sub('[^a-z0-9]','',t['name'].lower());assert name not in names,'Duplicate name';ids.add(t['id']);names.add(name)
  for field in ['meaning','why','example','experiment','caution','verifiedAt','addedAt','evidenceNote']:assert t.get(field),field
  assert t['source']['url'].startswith('https://') and len(t['how'])>=3,'Source/mechanism'
  assert len(t['poc']['steps'])>=3 and len(t['poc']['successCriteria'])>=2 and t['poc']['limitations'],'Incomplete POC'
 for item in data['items']:
  assert item['url'].startswith('https://') and item['id'] and item['title'],'Invalid source'
  assert len(item.get('summary','').split())<=25,'Source excerpt exceeds limit'
 assert len({i['id'] for i in data['items']})==len(data['items']),'Duplicate source IDs'
 return {'guides':len(data['terms']),'items':len(data['items']),'validation':'passed'}
if __name__=='__main__':print(json.dumps(validate(json.loads((ROOT/'public/data/publication.json').read_text()))))
