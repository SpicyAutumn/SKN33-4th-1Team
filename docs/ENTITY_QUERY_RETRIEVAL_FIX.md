# 인물명 검색 누락 수정 및 실제 서비스 검증

검증일: 2026-09-18. 기반 커밋: `84a33c7`.
작업 브랜치: `fix/entity-query-resolution`.

## 재현된 원인

`이순신 장군`을 초등학생 수준으로 질문하면 실제 Docker 서비스가
`insufficient_evidence`로 답했다. 데이터에 이순신이 없는 문제가 아니었다.
BM25 검색 1위에는 충무공 이순신(`aks:E0044900`)이 있었지만,
벡터 검색 상위 10건에는 해당 인물이 없었다.

기존 RRF의 `dense_weight=1.5`, `bm25_weight=1.0`, `rrf_k=60`에서는
벡터 검색 단독 10위 점수(1.5/70)가 BM25 단독 1위 점수(1/61)보다 높다.
최종 top_k=3을 선택할 때 이순신 문서가 탈락하고 `순장`, `이순몽 장군 묘`,
그릇을 뜻하는 `장군` 등이 전달됐다.

`이순신`만 입력하면 두 동명이인 문서를 찾았지만, 기존 동명이인 보호 규칙이
이름만 입력하는 형태를 인식하지 못했다. 실제 답변에서 충무공의 설명과
다른 이순신(`aks:E0044901`)의 선무공신 3등 기록이 섞였다.

## 수정 내용

- 검색 후보의 합집합을 유지한 뒤 질문에 명시된 표제어·별칭을 우선한다.
  그 다음 기존 문서당 청크 제한과 top_k를 적용한다.
- 명시된 별칭이 동명이인 중 하나에만 해당하면 다른 동명이인을 제외한다.
  인물 호칭은 인물/작품 구분에 사용하되 인물과 작품의 비교는 보존한다.
  특정 인물명이나 문서 ID를 운영 코드에 하드코딩하지 않는다.
- 이름 또는 이름+호칭만으로 동명이인을 구분할 수 없으면 기존 되묻기 흐름으로
  출처 기반 별칭과 정의를 선택지에 제공한다. 유명도만으로 인물을 선택하지 않는다.
- 규칙 기반 응답에도 현재 계약의 필수 `summary`를 넣는다.
- 현재 프론트가 보내는 `원래 질문 (선택지 문구)`를 출처에서 재구성한 문구와
  정확히 대조한다. 일치하면 선택지 설명 속 쉼표 때문에 복합 질문으로 오인하지 않는다.
- 모델에 전달하는 검색 근거에서 별칭과 자료 유형을 보존한다.

모델은 `qwen3.8:27b`, 기존 Runpod/Ollama 연결을 사용했다.
top_k=3, 검색 가중치, 시스템 프롬프트 지침, 프론트 코드는 변경하지 않았다.
모델 입력의 근거 메타데이터는 추가됐으므로 입력 토큰은 소폭 늘 수 있다.
추가 생성 모델 호출이나 별도 리랭커는 도입하지 않았다.

## 검증 결과

수정본을 기존 백엔드 이미지 위에 적용한 뒤 `http://localhost:8081/api/v1/searches`에
`audience_level=easy`로 실제 요청했다. 테스트는 비로그인으로 진행했다.

| 요청 | 적용 전 | 적용 후 실제 HTTP 결과 | 적용 후 시간 |
|---|---|---|---:|
| 이순신 장군 | 근거 부족, 이순신 문서 탈락 | 충무공/무의공 구분 선택지 | 3.658초 |
| 이순신 | 두 동명이인 내용 혼합 | 출처별 항목 선택지 | 3.100초 |
| 이순신 장군 → 충무공 선택 | 동일 경로 측정 없음 | answered, E0044900 인용, E0044901 미인용 | 13.688초 |
| 이순신 장군 → 무의공 선택 | 동일 경로 측정 없음 | answered, E0044901 인용, E0044900 미인용 | 12.585초 |

각 시간은 단일 요청 관측값이며 평균 성능 비교가 아니다. 두 되묻기 응답은
생성 모델을 호출하지 않는다. 선택지는 현재 UI와 같은 문자열로 재요청했다.
브라우저 화면 자동화가 아닌 프론트가 사용하는 실제 HTTP 경로 검증이다.

회귀 테스트: **176 passed, 180 subtests passed**.

```text
python -X utf8 -B -m pytest tests/test_entity_retrieval.py tests/test_hybrid_retriever.py tests/test_app_track_c.py tests/test_rag_service.py tests/test_ollama_generator.py --basetemp .pytest-tmp-entity-7 -p no:cacheprovider -q
```

추가 실제 호출에서는 `충무공 이순신`과 `경복궁 근정전`이 answered였다.
`김유신 장군`은 신라 장수와 근현대 독립운동가 항목을 찾아 되물었다.
이는 동명이인 혼합을 막는 보수적 동작이며 일반적인 검색 편의성까지 검증한 것은 아니다.

**남은 한계:** `무의공 이순신` 직접 입력은 E0044901을 정확히 선택했지만,
모델이 시호 관련 설명의 부족을 이유로 insufficient_evidence를 반환했다.
별칭 메타데이터 전달만으로 해결되지 않았다. 같은 인물을 화면의 전체 선택지로
선택한 경우는 정상 답변했다. 따라서 모든 인물 질문의 개선이나 전체 Dev/holdout
성능 향상을 주장하지 않는다. 기존 평가 결과와 이 변경 후 결과를 합산하지 않는다.

검색 우선순위는 이미 검색된 후보에 적용된다. 양쪽 검색 모두 후보를 놓치거나,
top_k보다 동명이인이 많은 경우까지 모두 해결하지는 않는다.

## 로컬 적용 및 기록

main의 코드와 기존 실험 기록은 수정하지 않았다.
별도 worktree `_local/entity-query-fix`에서 수정했고 로컬 Docker 백엔드에만 적용했다.

- 실행 이미지: `heritage-guide-backend:entity-query-fix`
- 실행 이미지 digest: `sha256:3aff1201c783084a08f84d743d5c72e9d64e93d5b5b90723d59d0dfb605b4563`
- 원본 보관 이미지: `heritage-guide-backend:before-entity-query-fix`
- 이미지 빌드/Compose override: `_local/live_checks/Dockerfile.entity-query-fix`, `compose.entity-query-fix.yml`
- 적용 전 검색 추적: `_local/live_checks/entity-retrieval-before.jsonl`
- 적용 전 HTTP 응답: `_local/live_checks/yi-sunsin-easy-20260918-163706.json`, `yi-sunsin-name-only-20260918-163829.json`
- 후보 검증 및 실패 기록: `_local/live_checks/entity-fix-candidate-validation*.jsonl`
- 추가 사례: `_local/live_checks/entity-fix-remaining-validation.jsonl`
- 최종 실제 HTTP 응답: `_local/live_checks/entity-fix-live-http.jsonl`

위 원응답/배포 보조 파일은 로컬 기록이며 이 코드 커밋에는 포함하지 않는다.
현재 Docker 적용은 override 이미지를 사용하므로 main에서 일반 재빌드하면 수정이
사라진다. 지속 적용하려면 이 브랜치를 리뷰·병합한 후 일반 이미지로 재빌드해야 한다.
main 병합이나 원격 push는 수행하지 않았다.
