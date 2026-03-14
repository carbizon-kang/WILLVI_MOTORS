"""매출 계산 로직 - 실무 매출내역서 양식 기준"""

ENGINE_OIL_UNIT_PRICE = 8750  # 엔진오일 실단가 (원/리터)
VAT_RATE = 0.1                # 부가세율 10%
PAINT_RATIO = 0.3             # 도장금액 비율 (총계×30%)


def calc_engine_oil(liter: float, unit_price: int = ENGINE_OIL_UNIT_PRICE) -> int:
    return round(liter * unit_price)


def calc_total_parts(parts: int, engine_oil: int, towing: int, insurance: int) -> int:
    return parts + engine_oil + towing + insurance


def calc_vat(tech_fee: int, rate: float = VAT_RATE) -> int:
    return round(tech_fee * rate)


def calc_total(parts: int, engine_oil: int, towing: int,
               insurance: int, tech_fee: int, vat_rate: float = VAT_RATE) -> int:
    total_parts = calc_total_parts(parts, engine_oil, towing, insurance)
    vat = calc_vat(tech_fee, vat_rate)
    return total_parts + tech_fee + vat


def calc_paint(total: int, ratio: float = PAINT_RATIO) -> int:
    return round(total * ratio)


def summarize_work_order(wo: dict) -> dict:
    """작업지시서 딕셔너리에서 계산 컬럼 보강"""
    liter = wo.get("engine_oil_liter", 0) or 0
    unit = wo.get("engine_oil_unit", ENGINE_OIL_UNIT_PRICE) or ENGINE_OIL_UNIT_PRICE
    parts = wo.get("parts_amount", 0) or 0
    towing = wo.get("towing_fee", 0) or 0
    insurance = wo.get("insurance_fee", 0) or 0
    tech = wo.get("tech_fee", 0) or 0
    vat_rate = wo.get("vat_rate", VAT_RATE) or VAT_RATE
    paint = wo.get("paint_amount", 0) or 0

    engine_oil = calc_engine_oil(liter, unit)
    total_parts = calc_total_parts(parts, engine_oil, towing, insurance)
    vat = calc_vat(tech, vat_rate)
    total = total_parts + tech + vat

    return {
        **wo,
        "engine_oil_amount": engine_oil,
        "total_parts": total_parts,
        "vat_amount": vat,
        "total_amount": total,
        "paint_calc": calc_paint(total),
    }


def fmt_money(val) -> str:
    """숫자 → '1,234,000원' 형식"""
    if val is None:
        return "-"
    return f"{int(val):,}원"
