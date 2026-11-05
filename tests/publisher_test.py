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
 def briefing_fixture(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research','title':'Local stopping decisions for reasoning models','summary':'The authors compare shorter continuations from the same reasoning prefixes and check whether each continuation retains a correct final answer. Their method learns a local stopping decision rather than imposing one length budget across every problem. Reported results are limited to the evaluated math and code tasks.'}
  selection={'url':source['url'],'signalType':'research','whatChanged':'The method learns local stopping decisions from shorter continuations checked for a correct final answer.','whyItMatters':'Teams building reasoning workflows can test whether shorter continuations preserve correctness on their own math and code cases.','evidenceQuote':'Their method learns a local stopping decision rather than imposing one length budget across every problem.','limitations':'The reported results cover the evaluated math and code tasks; other workloads need testing.'}
  return source,selection
 def test_briefing_rejects_routine_release_notes_even_with_feature_breaking_or_security_words(self):
  source,selection=self.briefing_fixture();source.update(kind='release',url='https://github.com/langchain-ai/langgraph/releases/tag/1.2.20',title='LangGraph 1.2.20',summary='feat: give each interrupt() in a task its own id. feat: add a strict resume mode that refuses stale interrupt answers. Breaking change CVE major release. '+source['summary']);selection['url']=source['url']
  now=dt.datetime(2026,11,5,tzinfo=dt.timezone.utc)
  self.assertEqual(publisher.select_briefing_candidates([source],now),[])
  with self.assertRaisesRegex(ValueError,'not eligible'):publisher.validate_briefing_selections([selection],[source],now)
  source['kind']='engineering'
  with self.assertRaisesRegex(ValueError,'not eligible'):publisher.validate_briefing_selections([selection],[source],now)
 def test_briefing_requires_collected_recent_source_and_exact_short_evidence(self):
  source,selection=self.briefing_fixture();now=dt.datetime(2026,11,5,tzinfo=dt.timezone.utc)
  result=publisher.validate_briefing_selections([selection],[source],now)
  self.assertEqual(result[0]['evidenceQuote'],selection['evidenceQuote']);self.assertEqual(result[0]['rank'],1)
  with self.assertRaisesRegex(ValueError,'not collected'):publisher.validate_briefing_selections([{**selection,'url':'https://uncollected.example/claim'}],[source],now)
  with self.assertRaisesRegex(ValueError,'evidence quote'):publisher.validate_briefing_selections([{**selection,'evidenceQuote':'This exact result was never stated by the collected source.'}],[source],now)
  with self.assertRaisesRegex(ValueError,'not eligible'):publisher.validate_briefing_selections([selection],[{**source,'publishedAt':'2026-10-01T00:00:00Z'}],now)
  with self.assertRaisesRegex(ValueError,'not eligible'):publisher.validate_briefing_selections([selection],[{**source,'publishedAt':'2026-11-07T00:00:00Z'}],now)
  with self.assertRaisesRegex(ValueError,'number absent'):publisher.validate_briefing_selections([{**selection,'whatChanged':'The method is 99% more accurate than every previous reasoning system.'}],[source],now)
 def test_selected_source_keeps_evidence_beyond_the_public_card_excerpt(self):
  source,selection=self.briefing_fixture();source.update(kind='engineering',url='https://example.org/workflow')
  selected=publisher.public_item(source,briefing=True)
  self.assertNotIn(selection['evidenceQuote'],selected['summary'])
  self.assertIn(selection['evidenceQuote'],selected['briefingSourceText'])
  self.assertLessEqual(len(selected['briefingSourceText']),6000)
  self.assertEqual(publisher.public_item(selected,briefing=True)['briefingSourceText'],selected['briefingSourceText'])
  self.assertNotIn('briefingSourceText',publisher.public_item(selected))
 def test_briefing_has_no_quota_and_cannot_select_duplicate_or_unbounded_records(self):
  source,selection=self.briefing_fixture();now=dt.datetime(2026,11,5,tzinfo=dt.timezone.utc)
  self.assertEqual(publisher.validate_briefing_selections([],[],now),[])
  with self.assertRaisesRegex(ValueError,'eight'):publisher.validate_briefing_selections([selection]*9,[source],now)
  with self.assertRaisesRegex(ValueError,'Duplicate'):publisher.validate_briefing_selections([selection,selection],[source],now)
  with self.assertRaisesRegex(ValueError,'concrete decision'):publisher.validate_briefing_selections([{**selection,'whyItMatters':'This is important for PMs who want to stay informed and keep up with current developments.'}],[source],now)
 def test_briefing_uses_one_bounded_selection_call_and_skips_thin_excerpts(self):
  source,_=self.briefing_fixture();now=dt.datetime(2026,11,5,tzinfo=dt.timezone.utc)
  items=[{**source,'sourceId':str(index),'url':'https://example.org/source-'+str(index),'summary':source['summary']*20} for index in range(20)]
  selected=publisher.select_briefing_candidates(items,now)
  self.assertLessEqual(len(selected),8);self.assertTrue(all(len(item['summary'])<=1400 for item in selected))
  with patch.object(publisher,'infer',return_value={'items':[]}) as model:
   self.assertEqual(publisher.generate_briefing(items,now),[]);self.assertEqual(model.call_count,1)
  with patch.object(publisher,'infer') as model:
   self.assertEqual(publisher.generate_briefing([{**source,'summary':'Title author date Go back to blog'}],now),[]);model.assert_not_called()
 def test_failed_briefing_preserves_prior_choices_and_original_missing_source_dates(self):
  source,selection=self.briefing_fixture();now=dt.datetime(2026,11,5,tzinfo=dt.timezone.utc)
  old={'schemaVersion':1,'generatedAt':'2026-11-04T08:00:00Z','status':'passed','items':[{**selection,'rank':1}]}
  previous={'briefing':old,'items':[publisher.public_item(source)]}
  with patch.object(publisher,'generate_briefing',side_effect=ValueError('Invalid editorial evidence')):
   result=publisher.refresh_briefing([],previous,now)
  self.assertEqual(result['status'],'failed');self.assertEqual(result['generatedAt'],old['generatedAt']);self.assertEqual(result['items'],old['items'])
  retained=publisher.retain_briefing_sources([],previous,result,now)
  self.assertEqual(retained[0]['publishedAt'],source['publishedAt']);self.assertEqual(retained[0]['url'],source['url'])
  with patch.object(publisher,'generate_briefing',return_value=[]):
   self.assertEqual(publisher.refresh_briefing([],previous,now)['items'],[])
  with patch.object(publisher,'generate_briefing',side_effect=ValueError('Unavailable')):
   self.assertEqual(publisher.refresh_briefing([],{**previous,'items':[{**source,'publishedAt':'2026-10-01T00:00:00Z'}]},now)['items'],[])
 def test_public_reader_retains_paper_abstracts_without_publishing_article_bodies(self):
  abstract='An author abstract with detailed methods and results. '*40
  paper=publisher.public_item({'url':'https://arxiv.org/abs/2611.05344','kind':'research','summary':abstract})
  self.assertEqual(paper['abstract'],abstract)
  self.assertEqual(len(paper['summary'].split()),25)
  article=publisher.public_item({'url':'https://example.com/article','kind':'engineering','summary':abstract})
  self.assertNotIn('abstract',article)
 def test_release_notes_keep_bullet_boundaries_in_publications(self):
  notes='Changes since 1.0\n\n* feat: add pause IDs\n* chore(deps): bump a dependency'
  item=publisher.public_item({'url':'https://github.com/o/r/releases/tag/v2','kind':'release','summary':notes,'releaseNotes':notes})
  self.assertEqual(item['releaseNotes'],notes)
  self.assertIn('\n* feat:',item['releaseNotes'])
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
 def test_model_versions_and_named_artifacts_cannot_become_vocabulary(self):
  cases=[('Dory1.0-4B','Dory1.0-4B is a 4-billion-parameter recurrent language model with elastic depth.'),('BEND 2.0','BEND 2.0 evaluates DNA language models on mutation effects.'),('Kronos','Kronos is a financial foundation model for forecasting market data.'),('FrontierPhysics','FrontierPhysics is an end-to-end benchmark of 56 physics research tasks.'),('CorpusX','CorpusX is a large dataset containing examples for training language models.'),('FlowKit','FlowKit is a Python library for building agent workflows.')]
  for name,meaning in cases:
   with self.subTest(name=name):
    guide=copy.deepcopy(self.guide);guide.update(id='candidate-'+publisher.norm(name),name=name,aliases=[],meaning=meaning)
    self.source.update(title=name,summary=meaning)
    with self.assertRaisesRegex(ValueError,'Vocabulary cannot'):self.validate(guide)
 def test_a_release_entry_cannot_be_the_source_for_a_vocabulary_guide(self):
  self.source['kind']='release'
  with self.assertRaisesRegex(ValueError,'reusable concept source'):self.validate()
 def test_concept_gate_retains_existing_concepts_classes_and_named_methods(self):
  values=[t for p in (ROOT/'public/data').glob('catalog-*.json') for t in json.loads(p.read_text())]+json.loads((ROOT/'public/data/publication.json').read_text())['terms']
  for guide in values:
   with self.subTest(name=guide['name']):publisher.validate_vocabulary_identity(guide,{'kind':'research'})
  for name,meaning in [('Looped language model','Looped language model is a recurrent language model that applies a shared block repeatedly.'),('Evaluation metric','Evaluation metric is a measurement method that compares model behavior with an explicit criterion.'),('ReAct','ReAct is an agent method that alternates reasoning, actions and observations.')]:
   publisher.validate_vocabulary_identity({'name':name,'meaning':meaning},{'kind':'research'})
 def test_ineligible_model_draft_is_rejected_before_designing_a_poc(self):
  guide=copy.deepcopy(self.guide);guide.update(id='candidate-dory',name='Dory1.0-4B',aliases=[],meaning='Dory1.0-4B is a recurrent language model with elastic depth.')
  source={**self.source,'title':guide['name'],'summary':guide['meaning'],'sourceId':'paper','priority':5,'layer':'Research'}
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',return_value={'terms':[guide]}) as model:
   with self.assertRaisesRegex(ValueError,'Vocabulary cannot'):publisher.generate([source],{},[])
   self.assertEqual(model.call_count,1)
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
   with patch.object(publisher,'ROOT',root),patch.object(publisher,'DATA',data),patch.object(publisher.sys,'argv',['refresh.py']),patch.object(publisher,'collect',return_value=([self.source],[{'error':None}]*5)),patch.object(publisher,'generate_briefing',side_effect=ValueError('Editorial evidence failed')),patch.object(publisher,'generate',side_effect=ValueError('Draft did not pass source review')):
    publisher.main()
   result=json.loads((data/'publication.json').read_text())
   self.assertEqual(result['guideStatus'],'failed');self.assertEqual(result['terms'],[self.guide]);self.assertEqual(result['items'][0]['url'],self.source['url']);self.assertEqual(result['newTermIds'],[])
   self.assertEqual(result['briefing']['status'],'failed');self.assertEqual(result['briefing']['items'],[])
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
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',side_effect=[{'terms':[self.guide]},self.guide['poc'],{'approvedIds':[],'issues':['Unsupported claim']},{'terms':[self.guide]},{'approvedIds':[],'issues':['Still unsupported']}] ):
   with self.assertRaisesRegex(ValueError,'rejected all'):publisher.generate([source],{},catalog)
 def test_review_feedback_can_repair_a_draft_before_publication(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research'}
  catalog=json.loads((ROOT/'publisher/catalog-index.json').read_text())
  responses=[{'terms':[self.guide]},self.guide['poc'],{'approvedIds':[self.guide['id']],'issues':['A check needs clarification']},{'terms':[self.guide]},{'approvedIds':[self.guide['id']],'issues':[]}]
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',side_effect=responses) as model:
   result=publisher.generate([source],{},catalog)
  self.assertEqual(result[0]['id'],self.guide['id']);self.assertIn('A check needs clarification',model.call_args_list[3].args[0])
 def test_no_daily_quota_can_publish_sources_without_a_fake_guide(self):
  source={**self.source,'sourceId':'paper','priority':5,'layer':'Research'}
  with patch.object(publisher,'NOW',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)),patch.object(publisher,'infer',return_value={'terms':[]}):
   self.assertEqual(publisher.generate([source],{},[]),[])

if __name__=='__main__':unittest.main()
