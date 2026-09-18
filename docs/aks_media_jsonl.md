# SKN33 4차 프로젝트 미디어 JSONL 생성기

## 검색 기능 담당자가 사용할 파일

최종 파일은 `data/processed/aks_article_medias.jsonl`입니다. 대표·관련 이미지가
함께 들어 있으므로 검색 기능에서는 이 파일 하나만 사용하면 됩니다.
JSONL은 팀 Google Drive로 전달하며 Git에는 생성 코드와 안내를 보관합니다.

- 검색된 청크의 `document_id`와 같은 문서를 찾아 `images`의 URL을 표시합니다.
- `role=head`는 대표 이미지, `role=related`는 관련 이미지입니다.
- 사진 아래에 `kogl_label`(공공누리 유형), `attribution`(출처),
  `copyright_display`(저작권 표시)를 표시하고 해당 유형의 이용 조건을 준수합니다.
- 같은 문서의 청크가 여러 개 검색되어도 그 문서의 사진은 한 번만 표시합니다.
- Django API가 검색 응답의 `citations[].document_id`로 이 파일을 조회해 `media`를
  반환하고, React 답변 화면이 사진·지도·도표와 공공누리 유형·출처를 표시합니다.
- 연결된 미디어가 없으면 `media`는 빈 배열이며 화면에는 텍스트만 표시합니다.
- API는 이미지 URL이 있고, 공공누리 유형이 `KOGL1`~`KOGL4`에 해당하는 이미지를
  반환합니다.
- 생성기는 모든 이미지에 `attribution`을 저장합니다. 이미지 제목이 있으면
  `제목, 『한국민족문화대백과사전』`, 제목이 없으면
  `『한국민족문화대백과사전』`을 출처로 사용합니다.
- 검색 기록에는 이미지를 복사해 저장하지 않습니다. 기록 상세의 `media`는 조회 시점의
  `aks_article_medias.jsonl`을 기준으로 다시 연결하므로 파일이 바뀌면 표시 결과도 달라질
  수 있습니다.
- 파일이 없거나 읽을 수 없거나 일부 행의 형식이 잘못된 경우에는 해당 미디어를 건너뛰고
  빈 배열을 반환하여 텍스트 검색 응답을 유지합니다.

재생성이 필요한 경우 3차 원본인 `aks_full_content.jsonl`과
`api_list_metadata` 폴더를 `data/raw`에 넣고 `scripts` 폴더의 실행 파일인
`scripts/build_related_medias_jsonl.py` → `scripts/build_head_medias_jsonl.py` →
`scripts/merge_article_medias_jsonl.py` 순서대로 PyCharm에서 실행하세요.

## 1. relatedMedias(관련 이미지) 버전

실행 파일: `scripts/build_related_medias_jsonl.py`

- 기존 `aks_full_content.jsonl`만 읽습니다.
- API를 추가 호출하지 않습니다.
- `mediaType=사진·지도·차트`이고 URL이 있는 자료 중
  `koglType=KOGL1~4`, 즉 공공누리 제1~4유형으로 확인된 자료만 추출합니다.
- 결과: `data/processed/aks_related_medias.jsonl`

## 2. headMedia(대표 이미지) 버전

실행 파일: `scripts/build_head_medias_jsonl.py`

- 항목 목록 API 원본인 `api_list_metadata/E*.json`의 `headMedia`를 읽습니다.
- `headMedia`에 URL과 공공누리 유형이 포함된 대표 사진·지도·차트를 저장합니다.
- 결과: `data/processed/aks_head_medias.jsonl`

두 결과 모두 청크 파일의 `document_id`(예: `aks:E0002434`)와 직접 대조할 수
있습니다.

## 3. 대표 이미지와 관련 이미지 통합

실행 파일: `scripts/merge_article_medias_jsonl.py`

앞의 두 파일을 실행한 다음 이 파일을 실행하면 됩니다. API를 추가 호출하지 않고
`document_id`를 기준으로 합치며, 대표 이미지는 `role=head`, 관련 이미지는
`role=related`로 저장합니다. 같은 문서(`document_id`) 안에서 같은 MID만 중복
제거하고 대표 이미지를 배열 맨 앞에 배치합니다. 서로 다른 문서에서 같은 MID를
사용하는 경우에는 각 문서와 이미지의 연결을 모두 유지합니다.

같은 MID가 대표·관련 목록에 모두 있으면 대표 이미지의 값을 우선합니다. 단, 대표
이미지의 제목·설명·저작권 표시·출처 등 일부 값이 비어 있으면 관련 이미지에 있던
값으로 보완합니다. 이미지 제목이 없는 경우에도 출처에는
`『한국민족문화대백과사전』`을 남깁니다.

- 결과: `data/processed/aks_article_medias.jsonl`

## 실행 결과

3차 프로젝트에서 수집한 `aks_full_content.jsonl`의 75,835개 항목과
`api_list_metadata/E*.json`의 75,835개 파일을 기준으로 실행한 결과입니다.

| 구분 | 문서 수 | 미디어 수 | 사진 | 지도 | 차트(도표) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 관련 미디어 | 22,098 | 57,935 | 57,889 | 44 | 2 |
| 대표 미디어 | 20,427 | 20,427 | 20,413 | 12 | 2 |
| 최종 통합 | 22,940 | 58,788 | 58,738 | 47 | 3 |

대표 미디어 20,427건 중 19,574건은 같은 문서의 관련 미디어에도 동일한 MID로
포함되어 있어 최종 통합 파일에 대표 미디어로 한 번만 저장했습니다. 관련 미디어에
없던 대표 미디어 853건은 최종 통합 배열에 새로 추가했습니다.

### 스크립트별 최종 출력과 의미

`build_related_medias_jsonl.py`

```text
필터 완료: 항목 75,835건 / 미디어 있는 항목 22,098건 / 미디어 57,935건
완료: data/processed/aks_related_medias.jsonl (22,098줄)
```

- 항목 75,835건: `aks_full_content.jsonl`에서 확인한 전체 항목 수
- 미디어 있는 항목 22,098건: 공공누리 제1~4유형의 관련 사진·지도·차트가 하나
  이상 있는 항목 수
- 미디어 57,935건: 조건을 충족해 저장한 관련 미디어 연결 수

`build_head_medias_jsonl.py`

```text
진행: 75,835/75,835 / 대표 미디어 20,427건 / 제외 55,408건
완료: data/processed/aks_head_medias.jsonl (20,427줄)
```

- 75,835/75,835: `api_list_metadata`의 전체 항목을 모두 확인했다는 의미
- 대표 미디어 20,427건: URL이 있고 공공누리 제1~4유형으로 확인된 대표
  사진·지도·차트 수
- 제외 55,408건: 위 조건을 충족하는 `headMedia`가 없어 결과에 저장하지 않은 항목
  수. 홈페이지에 미디어가 전혀 없다는 의미는 아님

`merge_article_medias_jsonl.py`

```text
관련 미디어: 57,935건
대표 미디어: 20,427건
관련 미디어와 동일한 대표 미디어: 19,574건
통합 배열에 새로 추가된 대표 미디어: 853건
완료: data/processed/aks_article_medias.jsonl (22,940줄)
```

- 관련 미디어와 대표 미디어의 MID가 같은 문서 안에서 겹치면 대표 미디어로 한 번만
  저장합니다.
- 관련 목록에 없던 대표 미디어 853건을 추가해 최종 58,788개의 미디어 연결을
  22,940개 문서에 저장합니다.
