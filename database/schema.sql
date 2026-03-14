-- WILLVI MOTORS VMS - Supabase SQL Editor에 전체 붙여넣기 후 실행
-- =====================================================================
-- 실행 순서: customers → parts → vehicles → work_orders → order_details → repair_photos → insurance_claims
-- =====================================================================

-- 1. 고객
CREATE TABLE IF NOT EXISTS customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    phone       TEXT,
    memo        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 부품 재고 (order_details가 참조하므로 vehicles보다 먼저 생성)
CREATE TABLE IF NOT EXISTS parts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    part_number TEXT,
    category    TEXT,
    unit_price  NUMERIC(12,0) DEFAULT 0,
    stock_qty   INTEGER DEFAULT 0,
    min_stock   INTEGER DEFAULT 0,
    supplier    TEXT,
    memo        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 차량
CREATE TABLE IF NOT EXISTS vehicles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    plate_number    TEXT NOT NULL,
    model           TEXT,
    color           TEXT,
    vin             TEXT,
    mileage         INTEGER,
    status          TEXT NOT NULL DEFAULT '입고'
                    CHECK (status IN ('입고','진단','수리중','부품대기','도장','상품화','출고완료')),
    intake_type     TEXT NOT NULL DEFAULT '일반(자비)'
                    CHECK (intake_type IN ('용답매입','용답데모','일반-삼성보험','일반-KB보험','일반-현대보험','일반-DB보험','일반(자비)')),
    intake_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_out    DATE,
    actual_out      DATE,
    aos_claimed     BOOLEAN DEFAULT FALSE,
    insurance_paid  NUMERIC(12,0),
    memo            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 작업지시서
CREATE TABLE IF NOT EXISTS work_orders (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id          UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    repair_seq          TEXT DEFAULT '수리1' CHECK (repair_seq IN ('수리1','수리2','추가')),
    description         TEXT,
    worker              TEXT,
    parts_amount        NUMERIC(12,0) DEFAULT 0,
    engine_oil_liter    NUMERIC(5,2) DEFAULT 0,
    engine_oil_unit     NUMERIC(8,0) DEFAULT 8750,
    engine_oil_amount   NUMERIC(12,0) GENERATED ALWAYS AS
                        (ROUND(engine_oil_liter * engine_oil_unit)) STORED,
    towing_fee          NUMERIC(12,0) DEFAULT 0,
    insurance_fee       NUMERIC(12,0) DEFAULT 0,
    tech_fee            NUMERIC(12,0) DEFAULT 0,
    paint_amount        NUMERIC(12,0) DEFAULT 0,
    vat_rate            NUMERIC(5,4) DEFAULT 0.1,
    total_parts         NUMERIC(12,0) GENERATED ALWAYS AS
                        (parts_amount + ROUND(engine_oil_liter * engine_oil_unit) + towing_fee + insurance_fee) STORED,
    vat_amount          NUMERIC(12,0) GENERATED ALWAYS AS
                        (ROUND(tech_fee * vat_rate)) STORED,
    total_amount        NUMERIC(12,0) GENERATED ALWAYS AS
                        (parts_amount + ROUND(engine_oil_liter * engine_oil_unit) + towing_fee + insurance_fee + tech_fee + ROUND(tech_fee * vat_rate)) STORED,
    status              TEXT DEFAULT '진행중' CHECK (status IN ('진행중','완료')),
    completed_at        DATE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 작업 세부 내역
CREATE TABLE IF NOT EXISTS order_details (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id   UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    item_type       TEXT DEFAULT '부품' CHECK (item_type IN ('부품','소모품','공임','기타')),
    item_name       TEXT NOT NULL,
    quantity        NUMERIC(10,2) DEFAULT 1,
    unit_price      NUMERIC(12,0) DEFAULT 0,
    amount          NUMERIC(12,0) GENERATED ALWAYS AS
                    (ROUND(quantity * unit_price)) STORED,
    part_id         UUID REFERENCES parts(id) ON DELETE SET NULL,
    memo            TEXT
);

-- 6. 수리 사진
CREATE TABLE IF NOT EXISTS repair_photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id      UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    work_order_id   UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    label           TEXT DEFAULT '기타'
                    CHECK (label IN ('입고전','수리중','출고전','기타')),
    file_url        TEXT NOT NULL,
    file_name       TEXT,
    taken_at        TIMESTAMPTZ DEFAULT NOW(),
    memo            TEXT
);

-- 7. 보험 청구
CREATE TABLE IF NOT EXISTS insurance_claims (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id      UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    work_order_id   UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    insurance_co    TEXT NOT NULL CHECK (insurance_co IN ('삼성화재','KB손보','현대해상','DB손보','기타')),
    vehicle_type    TEXT DEFAULT '국산' CHECK (vehicle_type IN ('국산','외산')),
    claim_amount    NUMERIC(12,0),
    deductible      NUMERIC(12,0) DEFAULT 0,
    fault_ratio     NUMERIC(5,2) DEFAULT 0,
    vat_applicable  BOOLEAN DEFAULT TRUE,
    aos_claimed_at  DATE,
    paid_amount     NUMERIC(12,0),
    paid_at         DATE,
    status          TEXT DEFAULT '청구전' CHECK (status IN ('청구전','청구완료','입금완료')),
    memo            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
