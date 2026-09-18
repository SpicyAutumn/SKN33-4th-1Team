-- 4차 프로젝트 MVP 서비스 DB 참고 스키마 초안 (PostgreSQL)
-- 현재 서비스는 Django ORM + MySQL을 사용하며 실제 스키마 기준은
-- backend/api/migrations/0004_service_v1_mysql.py 이다.
-- 이 파일은 PostgreSQL 설계 검토용이므로 현재 MySQL DB에 직접 적용하지 않는다.
-- 검색용 Pinecone 및 SQLite FTS5 인덱스는 이 스키마의 범위가 아니다.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email varchar(254) NOT NULL,
    password_hash text NOT NULL,
    name varchar(50) NOT NULL,
    role varchar(20) NOT NULL DEFAULT 'member'
        CHECK (role IN ('member', 'staff', 'admin')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (email = lower(email)),
    CHECK (length(btrim(name)) BETWEEN 1 AND 50),
    CHECK (length(password_hash) >= 20)
);

CREATE UNIQUE INDEX users_email_unique_idx ON users (lower(email));

CREATE TABLE auth_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash char(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    last_seen_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at > created_at)
);

CREATE INDEX auth_sessions_active_user_idx
    ON auth_sessions (user_id, expires_at DESC)
    WHERE revoked_at IS NULL;

CREATE TABLE search_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rag_request_id varchar(80) NOT NULL UNIQUE,
    interaction_id varchar(80) NOT NULL,
    schema_version varchar(30) NOT NULL,
    question text NOT NULL,
    audience_level varchar(20) NOT NULL
        CHECK (audience_level IN ('easy', 'general', 'advanced')),
    response_type varchar(40) NOT NULL
        CHECK (response_type IN (
            'answered',
            'insufficient_evidence',
            'needs_clarification',
            'corrected_premise',
            'safety_refusal',
            'out_of_scope'
        )),
    message text NOT NULL,
    clarification jsonb,
    premise_correction jsonb,
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, owner_user_id),
    CHECK (length(btrim(question)) BETWEEN 1 AND 1000),
    CHECK (length(btrim(message)) >= 1),
    CHECK (jsonb_typeof(warnings) = 'array')
);

CREATE INDEX search_records_owner_cursor_idx
    ON search_records (owner_user_id, created_at DESC, id DESC);
CREATE INDEX search_records_interaction_idx
    ON search_records (owner_user_id, interaction_id, created_at ASC);

CREATE TABLE search_citations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    search_record_id uuid NOT NULL REFERENCES search_records(id) ON DELETE CASCADE,
    ordinal smallint NOT NULL CHECK (ordinal >= 1),
    chunk_id text NOT NULL,
    document_id text NOT NULL,
    title text NOT NULL,
    source_url text,
    section text,
    retrieval_rank integer NOT NULL CHECK (retrieval_rank >= 1),
    content text NOT NULL,
    UNIQUE (search_record_id, ordinal),
    UNIQUE (search_record_id, chunk_id),
    CHECK (length(btrim(chunk_id)) >= 1),
    CHECK (length(btrim(document_id)) >= 1),
    CHECK (length(btrim(title)) >= 1),
    CHECK (length(btrim(content)) >= 1)
);

CREATE INDEX search_citations_record_idx
    ON search_citations (search_record_id, ordinal);

CREATE TABLE error_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    search_record_id uuid NOT NULL,
    category varchar(40) NOT NULL
        CHECK (category IN (
            'incorrect_fact',
            'citation_mismatch',
            'incomplete_answer',
            'inappropriate_content',
            'other'
        )),
    content text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'reviewing', 'resolved', 'rejected')),
    staff_reply text,
    handled_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    handled_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (length(btrim(content)) BETWEEN 10 AND 2000),
    CHECK (
        (handled_at IS NULL AND handled_by_user_id IS NULL)
        OR (handled_at IS NOT NULL AND handled_by_user_id IS NOT NULL)
    ),
    FOREIGN KEY (search_record_id, owner_user_id)
        REFERENCES search_records(id, owner_user_id)
        ON DELETE RESTRICT
);

CREATE INDEX error_reports_owner_cursor_idx
    ON error_reports (owner_user_id, created_at DESC, id DESC);
CREATE INDEX error_reports_status_cursor_idx
    ON error_reports (status, created_at ASC, id ASC);
CREATE INDEX error_reports_search_record_idx
    ON error_reports (search_record_id);

COMMENT ON TABLE search_records IS
    '회원별 RAG 질문과 최종 ServiceResponse의 재현 가능한 스냅샷';
COMMENT ON TABLE search_citations IS
    '검색 응답 시 사용자에게 표시한 출처 스냅샷';
COMMENT ON TABLE error_reports IS
    '회원 본인에게만 공개되는 검색 답변 연결 오류 제보';
