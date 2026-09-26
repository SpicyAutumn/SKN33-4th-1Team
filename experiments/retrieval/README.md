# 검색 비교 실험

`hybrid_retriever.py`는 문서별 청크 수 제한 등을 비교하는 실험 구현입니다. 실제 서비스 검색은 `src/rag_indexing/hybrid_retriever.py`를 사용합니다.

저장소 루트에서 기존 CLI를 실행합니다. 도움말은 외부 요청을 보내지 않습니다.

```sh
python scripts/experiment_hybrid_retrieval.py --help
python -m pytest tests/test_hybrid_retriever_experiment.py
```

실제 평가에는 데이터·검색 환경이 필요하며 외부 API 호출이 발생할 수 있습니다. 조건과 결과는 [기존 실험 보고서](../../docs/experiments/hybrid_retrieval_experiment_matrix.md)를 참고합니다.
