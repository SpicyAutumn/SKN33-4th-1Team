"""Synthetic offline responses: no model or network calls."""
import json
import unittest
from copy import deepcopy
from rag_service.ollama_generator import OllamaGenerator
from rag_service.ollama_generator import _clean_correction_summary
from unittest.mock import patch

class CorrectionSummaryTest(unittest.TestCase):
    def invoke(self, summary, *, detail=True, kind='answered', body=None, refs=True):
        text = body or '네, 맞습니다. 2001년이 아니라 2002년에 개관했습니다.'
        output = dict(candidate_response_type=kind,draft_message=text,
            used_chunk_ids=['CTX-1'] if refs else [],clarification=None,related_topic_candidates=[],
            premise_correction=dict(original_premise='2001년 개관',corrected_premise='2002년 개관',
                source_chunk_ids=['CTX-1'] if refs else []) if detail else None)
        if summary is not None:output['summary']=summary
        request=dict(schema_version='0.3.0-draft',request_id='summary-test',interaction_id='summary-test',
            question='가상 기록관은 2001년에 개관한 것이 맞지?',audience_level='general',
            response_language='ko',grounding_decision='sufficient',clarification_context=None,
            retrieved_contexts=[dict(chunk_id='fixture:1',document_id='fixture',title='가상 기록관',
                content='가상 기록관은 2002년에 개관했다.',source_url='https://example.test',
                section='body',retrieval_rank=1,retrieval_score=1,score_type='similarity',metadata={})])
        def transport(url,payload,timeout):
            return {'message':{'content':json.dumps(deepcopy(output),ensure_ascii=False)}}
        return OllamaGenerator(base_url='http://unused.invalid',model='offline-test',transport=transport).invoke(request)

    def test_generated_summary_cleaned_both_paths(self):
        for detail in (True,False):
            for prefix in ('네, 맞습니다. ','네. 맞습니다. ','예, 맞습니다. ','네, 맞습니다만 '):
                with self.subTest(detail=detail,prefix=prefix):
                    result=self.invoke(prefix+'2001년이 아니라 2002년입니다.',detail=detail)
                    self.assertEqual(result['summary'],'2001년이 아니라 2002년입니다.')
                    self.assertEqual(result['candidate_response_type'],'corrected_premise')

    def test_fallback_summary_cleaned(self):
        for detail in (True,False):
            with self.subTest(detail=detail):
                self.assertEqual(self.invoke(None,detail=detail)['summary'],
                                 '2001년이 아니라 2002년에 개관했습니다.')

    def test_summary_without_own_correction_unchanged(self):
        for text in ('네, 맞습니다.', '2002년에 개관했습니다.',
                     '네, 맞습니다. 전시뿐만 아니라, 다른 장르도 소개합니다.',
                     '네, 맞습니다. 전시뿐만 아니라 또 다른 분류도 소개합니다.',
                     '네, 맞습니다. 전시뿐만 아니라 조선의 다른 인물도 소개합니다.'):
            with self.subTest(text=text):self.assertEqual(self.invoke(text)['summary'],text)

    def test_normal_and_non_answer_unchanged(self):
        text='네, 맞습니다. 전시뿐만 아니라, 다른 장르도 소개합니다.'
        for kind in ('answered','safety_refusal','out_of_scope','needs_clarification','insufficient_evidence'):
            with self.subTest(kind=kind):
                result=self.invoke(text,detail=False,kind=kind,body='안내 문구입니다.',refs=kind=='answered')
                self.assertEqual(result['summary'],text)

    def test_already_clean_summary_unchanged(self):
        text='2001년이 아니라 2002년입니다.'
        self.assertEqual(self.invoke(text)['summary'],text)

    def test_helper_is_idempotent_and_preserves_other_fields(self):
        output = dict(candidate_response_type='corrected_premise',
                      summary='네, 맞습니다. 2001년이 아니라 2002년입니다.',
                      draft_message='본문 보존', used_chunk_ids=['fixture:1'])
        _clean_correction_summary(output)
        once = deepcopy(output)
        _clean_correction_summary(output)
        self.assertEqual(output, once)
        self.assertEqual(output['draft_message'], '본문 보존')
        self.assertEqual(output['used_chunk_ids'], ['fixture:1'])

    def test_helper_never_replaces_summary_with_empty_result(self):
        output = dict(candidate_response_type='corrected_premise',
                      summary='네, 맞습니다. 잘못된 연도입니다.')
        original = deepcopy(output)
        with patch('rag_service.ollama_generator._clean_correction_message', return_value=''):
            _clean_correction_summary(output)
        self.assertEqual(output, original)

    def test_no_evidence_downgrade_preserves_summary(self):
        text = '네, 맞습니다. 2001년이 아니라 2002년입니다.'
        result = self.invoke(text, detail=False, refs=False)
        self.assertEqual(result['candidate_response_type'], 'insufficient_evidence')
        self.assertEqual(result['summary'], text)
