"""Publication boundaries that must hold before unattended writes."""
import copy, datetime as dt, importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frontier_publisher',ROOT/'publisher/refresh.py')
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)

class PublisherTests(unittest.TestCase):
 def setUp(self):
  self.guide=json.loads((ROOT/'public/data/publication.json').read_text())['terms'][0]
  self.source={'url':self.guide['source']['url'],'title':self.guide['name'],'summary':self.guide['meaning'],'source':'Test paper','kind':'research','publishedAt':'2026-11-03T12:00:00+00:00'}
 def validate(self,guide=None,known=None):
  catalog=json.loads((ROOT/'publisher/catalog-index.json').read_text())
  return publisher.validate_terms([copy.deepcopy(guide or self.guide)],[self.source],catalog+(known or []),'2026-11-04T12:00:00+00:00')
 def test_hn_self_posts_remain_distinct(self):
  self.assertNotEqual(publisher.canonical('https://news.ycombinator.com/item?id=1'),publisher.canonical('https://news.ycombinator.com/item?id=2'))
 def test_tracking_and_paper_versions_deduplicate(self):
  self.assertEqual(publisher.canonical('https://arxiv.org/abs/2611.04814v2?utm_source=x'),publisher.canonical('https://huggingface.co/papers/2611.04814'))
 def test_source_instructions_are_not_executed_or_rendered(self):
  self.assertEqual(publisher.plain('<script>send credentials()</script><main>LoCo reasoning</main>'),'LoCo reasoning')
  bad=copy.deepcopy(self.guide);bad['source']['url']='https://uncollected.example/instructions'
  with self.assertRaisesRegex(ValueError,'not collected'):self.validate(bad)
 def test_existing_id_and_first_date_are_preserved(self):
  old={**self.guide,'addedAt':'2026-10-01T00:00:00Z'}
  self.assertEqual(self.validate(known=[old])[0]['addedAt'],old['addedAt'])
  bad=copy.deepcopy(self.guide);bad['id']='replacement-id'
  with self.assertRaisesRegex(ValueError,'original ID'):self.validate(bad,[old])
 def test_short_poc_cannot_ask_for_frontier_model_training(self):
  bad=copy.deepcopy(self.guide);bad['poc']['steps'][0]='Train a draft model on agent trajectories.'
  with self.assertRaisesRegex(ValueError,'model training'):self.validate(bad)
 def test_negated_training_requirement_does_not_reject_a_local_exercise(self):
  guide=copy.deepcopy(self.guide);guide['poc']['requirements']=['No GPU required.','No training or fine-tuning.','Python standard library.']
  self.assertEqual(self.validate(guide)[0]['poc']['requirements'],guide['poc']['requirements'])
 def test_negation_cannot_hide_a_later_affirmative_training_step(self):
  bad=copy.deepcopy(self.guide);bad['poc']['steps'][0]='No GPU required. Train a frontier model on agent traces.'
  with self.assertRaisesRegex(ValueError,'model training'):self.validate(bad)
  bad['poc']['requirements']=['No GPU required'];bad['poc']['steps'][0]='Train a frontier model on agent traces.'
  with self.assertRaisesRegex(ValueError,'model training'):self.validate(bad)
 def test_poc_checks_need_a_concrete_count_or_threshold(self):
  bad=copy.deepcopy(self.guide);bad['poc']['successCriteria']=['1. Improved accuracy.','2. Better reasoning.']
  with self.assertRaisesRegex(ValueError,'sample size'):self.validate(bad)
 def test_experimental_results_cannot_be_called_noise_free(self):
  bad=copy.deepcopy(self.guide);bad['meaning']='This method produces noise-free reasoning at every decision point.'
  with self.assertRaisesRegex(ValueError,'overstates'):self.validate(bad)
 def test_incomplete_poc_is_rejected(self):
  bad=copy.deepcopy(self.guide);bad['poc']['successCriteria']=[]
  with self.assertRaisesRegex(ValueError,'checks'):self.validate(bad)
 def test_future_sources_cannot_generate_guides(self):
  future={**self.source,'publishedAt':'2099-11-04T00:00:00+00:00'}
  with self.assertRaisesRegex(ValueError,'No recent source'):publisher.generate([future],{},[])
 def test_already_covered_article_is_not_rewritten_as_daily_news(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research'}
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer') as model:
   self.assertEqual(publisher.generate([source],{'terms':[self.guide]},[]),[])
   model.assert_not_called()
 def test_primary_source_survives_hn_duplicate(self):
  sources=[{'id':'lab','priority':5},{'id':'hn','priority':2}]
  rows={'lab':{**self.source,'sourceId':'lab','priority':5,'id':'same'},'hn':{**self.source,'kind':'discussion','sourceId':'hn','priority':2,'points':42,'id':'same'}}
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);(path/'sources.json').write_text(json.dumps(sources))
   with patch.object(publisher,'DATA',path),patch.object(publisher,'collect_source',side_effect=lambda s:[rows[s['id']]]):
    # The production threshold intentionally requires at least five healthy sources.
    sources.extend({'id':'extra'+str(i),'priority':1} for i in range(3));(path/'sources.json').write_text(json.dumps(sources))
    for s in sources[2:]:rows[s['id']]={**self.source,'url':'https://example.com/'+s['id'],'sourceId':s['id'],'priority':1,'id':s['id']}
    items,_=publisher.collect({})
   primary=next(i for i in items if i['url']==self.source['url'])
   self.assertEqual(primary['sourceId'],'lab');self.assertEqual(primary['points'],42)

 def test_failed_guide_generation_still_publishes_valid_sources(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'public/data';data.mkdir(parents=True)
   (root/'publisher').mkdir();(root/'publisher/catalog-index.json').write_text('[]')
   (data/'publication.json').write_text(json.dumps({'terms':[self.guide],'items':[]}))
   with patch.object(publisher,'ROOT',root),patch.object(publisher,'DATA',data),patch.object(publisher.sys,'argv',['refresh.py']),patch.object(publisher,'collect',return_value=([self.source],[{'error':None}]*5)),patch.object(publisher,'generate',side_effect=ValueError('Draft did not pass source review')):
    publisher.main()
   result=json.loads((data/'publication.json').read_text())
   self.assertEqual(result['guideStatus'],'failed');self.assertEqual(result['terms'],[self.guide]);self.assertEqual(result['items'][0]['url'],self.source['url']);self.assertEqual(result['newTermIds'],[])
 def test_papers_and_practitioners_are_not_crowded_out_by_labs(self):
  now=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)
  items=[{**self.source,'title':'Agent model training '+str(i),'url':'https://example.com/'+str(i),'sourceId':str(i),'priority':5,'layer':'Labs'} for i in range(10)]
  items.extend({**self.source,'sourceId':layer,'priority':4,'layer':layer} for layer in ['Research','Engineering','Practitioners'])
  selected=publisher.select_candidates(items,now)
  self.assertEqual({s['layer'] for s in selected},{'Research','Engineering','Practitioners','Labs'})
  self.assertLessEqual(len(selected),8)
 def test_source_check_rejection_prevents_publication(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research'}
  catalog=json.loads((ROOT/'publisher/catalog-index.json').read_text())
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',side_effect=[{'terms':[self.guide]},self.guide['poc'],{'approvedIds':[],'issues':['Unsupported claim']} ]):
   with self.assertRaisesRegex(ValueError,'rejected all'):publisher.generate([source],{},catalog)
 def test_no_daily_quota_can_publish_sources_without_a_fake_guide(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research'}
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',return_value={'terms':[]}):
   self.assertEqual(publisher.generate([source],{},[]),[])

if __name__=='__main__':unittest.main()
