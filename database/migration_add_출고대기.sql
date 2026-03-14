-- vehicles 테이블 status CHECK 제약에 '출고대기' 추가
-- Supabase SQL Editor에서 실행

ALTER TABLE vehicles
  DROP CONSTRAINT IF EXISTS vehicles_status_check;

ALTER TABLE vehicles
  ADD CONSTRAINT vehicles_status_check
  CHECK (status IN ('입고','진단','수리중','부품대기','도장','상품화','출고대기','출고완료'));
