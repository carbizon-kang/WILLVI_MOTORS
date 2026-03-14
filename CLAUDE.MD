# WILLVI MOTORS VMS (Vehicle Management System) 마스터 설계서

> **최종 업데이트**: 2026-03-11
> **작성 기준**: 실무 엑셀 양식 분석 (2026작업진행내역, 26년1월 매출내역서)

---

## 1. 프로젝트 개요

### 1.1 배경 및 목적
WILLVI MOTORS는 인증 중고차 상품화 및 차량 수리 전반을 담당하는 자회사로,
현재 아래 업무를 **수기/엑셀로 관리**하고 있어 전산화가 시급한 상황이다.

| 현재 문제점 | 전산화 후 기대 효과 |
|---|---|
| 엑셀 작업진행내역 수기 입력 | 실시간 차량 상태 조회 |
| 매출내역 수식 기반 엑셀 관리 | 자동 집계 및 월별/보험사별 리포트 |
| 보험 청구 현황 수기 추적 | 청구→입금 전 과정 추적 |
| 수리 사진 별도 보관 | 차량별 사진 통합 관리 |
| 부품/기술료 수기 계산 | 견적서 자동 생성 |
| 고객 연락처 산재 | 고객 이력 통합 조회 |

### 1.2 시스템 범위
- **입고 관리**: 일반/보험/용답매입/용답데모 차량 접수
- **수리 관리**: 작업 상태 추적, 수리 내역, 부품 관리
- **매출 관리**: 부품비·기술료·도장비·보험료 자동 집계
- **보험 청구 관리**: 보험사별 청구·AOS·입금 추적
- **고객 관리**: 고객 이력, 차량 정보, 사진 관리
- **사진 관리**: 수리 전·중·후 사진 업로드 및 조회

---

## 2. 비즈니스 도메인 분석

### 2.1 입고 분류 체계 (실무 기준)

```
입고분류
├── 용답매입      ← 용답 딜러망을 통해 매입한 차량 상품화
├── 용답데모      ← 한성자동차 DMS 연계 데모 차량 상품화
├── 일반-삼성보험  ← 삼성화재 보험 사고 수리
├── 일반-KB보험   ← KB손보 보험 사고 수리
├── 일반-현대보험  ← 현대해상 보험 사고 수리
├── 일반-DB보험   ← DB손보 보험 사고 수리
└── 일반(자비)    ← 보험 미적용 일반 수리
```

### 2.2 차량 수리 진행 상태 (Status Flow)

```
[입고] → [진단] → [수리중] → [부품대기] → [도장/판금] → [상품화] → [출고완료]
                                                              ↑
                                                    (용답매입/데모 차량)
```

- `수리1`, `수리2`: 1차 수리 → 2차 수리(재작업 또는 추가 수리) 구분
- `작업 상태`: 실시간 진행 단계
- `출고예정일`: 고객 안내용 예상 완료일

### 2.3 매출 구조 (실무 엑셀 기준)

```
총계 = 총부품금액 + 기술료 + 부가가치세
     = (부품금액 + 엔진오일 + 견인비 + 보험료) + 기술료 + (기술료 × 부가세율)

도장금액 = 총계 × 30% (별도 집계)

엔진오일 실단가: 8,750원/리터 (기준 단가, 변동 가능)
```

| 매출 항목 | 설명 |
|---|---|
| 부품금액 | 사용 부품 합계 (엔진오일 제외) |
| 엔진오일 | 리터 × 실단가(8,750원) |
| 견인비 | 입고 시 견인 비용 |
| 보험료 | 보험사 청구 금액 |
| 기술료 | 공임(작업 기술 비용) |
| 부가가치세 | 기술료에 부과 |
| 도장금액 | 총계의 30% (판금도색 포함 시) |

### 2.4 보험사 업무 체계

| 보험사 | 국산/외산 구분 | 주요 확인 사항 |
|---|---|---|
| 삼성화재 | 외산/국산 분리 | 자기부담금, 과실여부, 부가세 |
| 현대해상 | 외산/국산 분리 | 동일 |
| KB손보 | 외산/국산 분리 | 동일 |
| DB손보 | 외산/국산 분리 | 동일 |

- **AOS**: 보험사 정산 시스템 청구 여부 (Y/N)
- **보험입금**: 보험사로부터 실제 입금된 금액/일자
- **한성자동차 DMS**: 데모 차량 사고 유무 확인 시스템 (담당: 최동진 차장)

---

## 3. 데이터 모델 (DB Schema)

### 3.1 테이블 구조

#### `customers` (고객)
```sql
id              UUID PRIMARY KEY
name            TEXT NOT NULL          -- 고객명
phone           TEXT                   -- 연락처
memo            TEXT                   -- 비고
created_at      TIMESTAMPTZ DEFAULT NOW()
```

#### `vehicles` (차량)
```sql
id              UUID PRIMARY KEY
customer_id     UUID REFERENCES customers
plate_number    TEXT NOT NULL          -- 차량번호 (예: 12가3456)
model           TEXT                   -- 차량모델 (예: BMW 520d)
color           TEXT                   -- 차량색상
vin             TEXT                   -- 차대번호
mileage         INTEGER                -- 입고 시 주행거리
status          TEXT DEFAULT '입고'    -- 입고/진단/수리중/부품대기/도장/상품화/출고완료
intake_type     TEXT                   -- 용답매입/용답데모/일반-삼성/일반-KB/일반-현대/일반-DB/일반(자비)
intake_date     DATE                   -- 입고일
expected_out    DATE                   -- 출고예정일
actual_out      DATE                   -- 실제출고일
aos_claimed     BOOLEAN DEFAULT FALSE  -- AOS 청구 여부
insurance_paid  NUMERIC(12,0)          -- 보험입금액
memo            TEXT                   -- 비고
created_at      TIMESTAMPTZ DEFAULT NOW()
```

#### `work_orders` (작업지시서)
```sql
id              UUID PRIMARY KEY
vehicle_id      UUID REFERENCES vehicles
repair_type     TEXT                   -- 수리1/수리2 구분
description     TEXT                   -- 수리내용
worker          TEXT                   -- 담당 기술자
parts_amount    NUMERIC(12,0) DEFAULT 0  -- 부품금액 (엔진오일 제외)
engine_oil_liter NUMERIC(5,2)           -- 엔진오일 리터 수
engine_oil_unit  NUMERIC(8,0) DEFAULT 8750  -- 엔진오일 실단가
towing_fee      NUMERIC(12,0) DEFAULT 0   -- 견인비
insurance_fee   NUMERIC(12,0) DEFAULT 0   -- 보험료
tech_fee        NUMERIC(12,0) DEFAULT 0   -- 기술료
paint_amount    NUMERIC(12,0) DEFAULT 0   -- 도장금액
vat_rate        NUMERIC(5,4) DEFAULT 0.1  -- 부가세율
-- 계산 컬럼 (자동)
engine_oil_amount  NUMERIC(12,0)  -- engine_oil_liter × engine_oil_unit
total_parts        NUMERIC(12,0)  -- parts_amount + engine_oil_amount + towing_fee + insurance_fee
vat_amount         NUMERIC(12,0)  -- tech_fee × vat_rate
total_amount       NUMERIC(12,0)  -- total_parts + tech_fee + vat_amount
status          TEXT DEFAULT '진행중'  -- 진행중/완료
completed_at    DATE
created_at      TIMESTAMPTZ DEFAULT NOW()
```

#### `order_details` (작업 세부 내역 / 부품 사용 내역)
```sql
id              UUID PRIMARY KEY
work_order_id   UUID REFERENCES work_orders
item_type       TEXT                   -- 부품/소모품/공임
item_name       TEXT NOT NULL          -- 항목명
quantity        NUMERIC(10,2) DEFAULT 1
unit_price      NUMERIC(12,0) DEFAULT 0
amount          NUMERIC(12,0)          -- quantity × unit_price (트리거 자동)
part_id         UUID REFERENCES parts  -- 부품 재고 연결 (nullable)
memo            TEXT
```

#### `parts` (부품 재고)
```sql
id              UUID PRIMARY KEY
name            TEXT NOT NULL
part_number     TEXT                   -- 부품번호
category        TEXT                   -- 엔진/외장/전기/소모품 등
unit_price      NUMERIC(12,0) DEFAULT 0
stock_qty       INTEGER DEFAULT 0
min_stock       INTEGER DEFAULT 0      -- 최소 재고 (알림 기준)
supplier        TEXT                   -- 공급업체
memo            TEXT
```

#### `repair_photos` (수리 사진)
```sql
id              UUID PRIMARY KEY
vehicle_id      UUID REFERENCES vehicles
work_order_id   UUID REFERENCES work_orders  -- nullable
label           TEXT                   -- 입고전/수리중/출고전/기타
file_url        TEXT NOT NULL          -- Supabase Storage URL
file_name       TEXT
taken_at        TIMESTAMPTZ DEFAULT NOW()
memo            TEXT
```

#### `insurance_claims` (보험 청구 관리)
```sql
id              UUID PRIMARY KEY
vehicle_id      UUID REFERENCES vehicles
work_order_id   UUID REFERENCES work_orders
insurance_co    TEXT                   -- 삼성/KB/현대/DB
vehicle_type    TEXT                   -- 국산/외산
claim_amount    NUMERIC(12,0)          -- 청구금액
deductible      NUMERIC(12,0)          -- 자기부담금
fault_ratio     NUMERIC(5,2)           -- 과실비율 (%)
vat_applicable  BOOLEAN DEFAULT TRUE   -- 부가세 적용 여부
aos_claimed_at  DATE                   -- AOS 청구일
paid_amount     NUMERIC(12,0)          -- 입금액
paid_at         DATE                   -- 입금일
status          TEXT DEFAULT '청구전'  -- 청구전/청구완료/입금완료
memo            TEXT
```

---

## 4. 기능 요구사항

### 4.1 대시보드 (홈)
- [ ] 현재 입고 차량 현황 (상태별 카운트)
- [ ] 오늘 입고 / 오늘 출고 예정 차량 목록
- [ ] 이번 달 매출 요약 (부품/기술료/도장 분리)
- [ ] 보험 청구 미입금 건수 및 금액
- [ ] 부품 재고 부족 알림

### 4.2 차량 입고 등록
- [ ] 입고 분류 선택 (용답매입/용답데모/일반-보험사/일반자비)
- [ ] 차량 정보 입력 (번호판, 모델, 고객)
- [ ] 기존 고객 검색 또는 신규 고객 등록
- [ ] 입고 사진 업로드 (입고 전 상태)
- [ ] 보험 사고 정보 입력 (보험사 선택, 자기부담금, 과실비율)

### 4.3 차량 현황 조회 / 작업 관리
- [ ] 전체 차량 목록 (필터: 상태별, 입고분류별, 날짜별)
- [ ] 차량별 상세 페이지
  - [ ] 기본 정보 (차량번호, 모델, 고객, 입고일)
  - [ ] 수리 진행 상태 변경
  - [ ] 수리 내용 입력 (수리1, 수리2 구분)
  - [ ] 수리 사진 업로드/조회
  - [ ] 작업지시서 생성 및 비용 입력
- [ ] Kanban 뷰: 상태별 차량 카드 배치 (드래그 이동)

### 4.4 매출 관리
- [ ] 월별 매출 현황 (실무 엑셀 형식 유사)
- [ ] 입고분류별 매출 분석 (용답매입/데모/보험사별)
- [ ] 자동 계산: 부품금액 + 엔진오일 + 견인비 + 기술료 + 부가세 = 총계
- [ ] 도장금액 자동 계산 (총계 × 30%)
- [ ] 엑셀 내보내기 (현재 매출내역서 양식 호환)

### 4.5 보험 청구 관리
- [ ] 보험사별 청구 현황 (청구전/청구완료/입금완료)
- [ ] AOS 청구 등록 및 추적
- [ ] 보험 입금 등록
- [ ] 보험사별 미수금 현황

### 4.6 고객 관리
- [ ] 고객 목록 / 검색 (이름, 전화번호)
- [ ] 고객별 차량 수리 이력
- [ ] 고객 메모

### 4.7 부품 재고 관리
- [ ] 부품 목록 / 재고 현황
- [ ] 작업지시서 연동 자동 재고 차감
- [ ] 최소 재고 이하 알림

### 4.8 사진 관리
- [ ] 차량별 사진 갤러리 (입고전 / 수리중 / 출고전 / 기타)
- [ ] 사진 업로드 (카메라/파일)
- [ ] 사진 공유 링크 생성 (고객 전송용)

---

## 5. 화면 구조 (Streamlit 기준)

```
앱 메뉴
├── 🏠 대시보드
├── 🚗 차량 관리
│   ├── 입고 등록
│   ├── 차량 현황 (전체 목록 / Kanban)
│   └── 차량 상세
├── 🔧 작업 관리
│   ├── 작업지시서 목록
│   └── 작업지시서 상세 / 입력
├── 💰 매출 관리
│   ├── 월별 매출 현황
│   └── 입고분류별 분석
├── 🏦 보험 청구
│   ├── 청구 현황
│   └── 보험사별 정산
├── 👤 고객 관리
├── 📦 부품 재고
└── 📸 사진 관리
```

---

## 6. 기술 스택

| 구분 | 기술 |
|---|---|
| Frontend / App | Streamlit |
| Backend DB | Supabase (PostgreSQL) |
| Storage | Supabase Storage (사진 파일) |
| 인증 | Supabase Auth |
| 언어 | Python 3.11+ |
| 배포 | Streamlit Cloud 또는 내부 서버 |

### 6.1 핵심 Python 패키지
```
streamlit
supabase
python-dotenv
pandas
openpyxl         # 엑셀 내보내기
pillow           # 이미지 처리
plotly           # 차트
```

---

## 7. 개발 단계 계획

### Step 1 (완료) - 환경 설정
- [x] 프로젝트 구조 생성
- [x] DB 스키마 설계
- [x] Supabase 연결 설정

### Step 2 - 핵심 입출고 기능
- [ ] 차량 입고 등록 화면
- [ ] 차량 현황 목록 (필터링)
- [ ] 차량 상태 변경

### Step 3 - 수리 및 비용 관리
- [ ] 작업지시서 CRUD
- [ ] 비용 자동 계산 (매출내역서 양식)
- [ ] 보험 청구 등록

### Step 4 - 매출 / 보험 리포트
- [ ] 월별 매출 대시보드
- [ ] 보험사별 정산 현황
- [ ] 엑셀 내보내기

### Step 5 - 고객 / 사진 / 부품
- [ ] 고객 관리
- [ ] 사진 업로드/조회 (Supabase Storage)
- [ ] 부품 재고 관리

---

## 8. 주요 업무 흐름 (Business Flow)

### 8.1 일반 수리 차량 흐름
```
고객 내방/연락
→ 차량 입고 등록 (입고일, 차량번호, 고객정보, 입고분류)
→ 차량 상태: 입고
→ 진단 완료 → 상태: 진단완료
→ 수리 작업지시서 발행 (수리1)
→ 상태: 수리중
→ 부품 필요 시 → 상태: 부품대기
→ 수리 완료 → 수리내용/비용 입력
→ 도장/판금 필요 시 → 상태: 도장
→ 출고 준비 → 사진 촬영
→ 비용 청구 → 입금 확인
→ 상태: 출고완료
```

### 8.2 보험 차량 흐름
```
보험 사고 접수 (보험사 연락)
→ 차량 입고 등록 (입고분류: 일반-XX보험)
→ 보험사 정보 입력 (자기부담금, 과실비율, 국산/외산)
→ 수리 진행 (작업지시서)
→ AOS 시스템 청구 (AOS = Y)
→ 보험사 입금 확인
→ 입금 등록 (보험입금액)
→ 출고완료
```

### 8.3 용답 차량 흐름 (매입/데모)
```
용답 매입 or 한성자동차 DMS 데모 차량
→ 입고 등록 (입고분류: 용답매입 or 용답데모)
  └─ 데모 차량은 한성 DMS 사고 유무 확인 (최동진 차장)
→ 상품화 작업 (부품 교환, 도장, 정비)
→ 상태: 상품화
→ 상품화 완료 → 출고
```

---

## 9. 기타 참고 정보

### 9.1 협력업체 연락처 (시스템 내 관리 권고)
| 업체 | 담당자 | 연락처 | 비고 |
|---|---|---|---|
| 한성자동차 | 최동진 차장 | 010-8668-7142 | 용답 어드바이져 사고 문의, DMS 확인 |
| 쌍성타이어 | 나상율 부사장 | 02-2244-6407 | 타이어 공급 |

### 9.2 보험사별 특이사항
- **공통**: 국산/외산 구분하여 수가 적용
- **삼성화재**: 자기부담금, 과실여부, 부가세 확인 필수
- **한성자동차 연계**: 데모 차량은 DMS에서 사고이력 반드시 확인

### 9.3 엔진오일 단가 기준
- 기준 단가: 8,750원/리터 (2025년 말 기준, 변경 가능)
- 7리터 기준 총액: 61,250원 (공식: 8,750 × 7)
- 시스템에서 단가를 수정 가능한 파라미터로 관리

---

## 10. 파일 구조

```
WILLVI_MOTORS/
├── CLAUDE.MD                        # 마스터 설계서 (이 파일)
├── .env                             # 환경변수 (Supabase keys)
├── .env.example                     # 환경변수 템플릿
├── requirements.txt                 # Python 패키지
├── app.py                           # Streamlit 앱 진입점
│
├── database/
│   ├── __init__.py
│   ├── connection.py                # Supabase 클라이언트 싱글턴
│   ├── models.py                    # SQL 쿼리 상수
│   └── schema.sql                   # Supabase SQL Editor 실행용
│
├── pages/
│   ├── 01_dashboard.py              # 대시보드
│   ├── 02_vehicle_intake.py         # 차량 입고 등록
│   ├── 03_vehicle_list.py           # 차량 현황 / Kanban
│   ├── 04_vehicle_detail.py         # 차량 상세 / 작업지시서
│   ├── 05_sales_report.py           # 매출 관리
│   ├── 06_insurance_claims.py       # 보험 청구 관리
│   ├── 07_customers.py              # 고객 관리
│   ├── 08_parts.py                  # 부품 재고
│   └── 09_photos.py                 # 사진 관리
│
└── utils/
    ├── calculations.py              # 매출 계산 로직
    ├── excel_export.py              # 엑셀 내보내기
    └── photo_upload.py              # Supabase Storage 업로드
```
