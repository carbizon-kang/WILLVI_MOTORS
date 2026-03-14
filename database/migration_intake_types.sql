-- 입고분류 관리 테이블
-- Supabase SQL Editor에서 실행

CREATE TABLE IF NOT EXISTS intake_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    is_insurance BOOLEAN DEFAULT FALSE,  -- 보험 청구 여부 (True면 보험사 정보 입력 필요)
    sort_order  INTEGER DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 항목 삽입
INSERT INTO intake_types (name, is_insurance, sort_order) VALUES
  ('용답매입',      FALSE, 1),
  ('용답데모',      FALSE, 2),
  ('일반-삼성보험', TRUE,  3),
  ('일반-KB보험',   TRUE,  4),
  ('일반-현대보험', TRUE,  5),
  ('일반-DB보험',   TRUE,  6),
  ('일반(자비)',    FALSE, 7)
ON CONFLICT (name) DO NOTHING;
