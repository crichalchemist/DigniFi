"""The 122A-2 page's answers: their keys, how a stale reference reads, and the page's gaps. Pure: no models, no forms module."""

ANSWER_KEYS: tuple[str, ...] = (
    "line_3_answer",
    "line_3_rows",
    "spouse_vehicles_answer",
    "spouse_vehicles",
    "spouse_loans_answer",
    "spouse_loans",
    "vehicle_claims",
    "vehicle_choice",
    "line_15_answer",
    "line_15_amount",
    "line_16",
    "line_17",
    "line_18",
    "line_19",
    "line_20",
    "line_21",
    "line_22_answer",
    "line_22_amount",
    "line_23",
    "line_25_answer",
    "line_25_health",
    "line_25_disability",
    "line_25_hsa",
    "line_25_spends",
    "line_25_actual",
    *(f"line_{n}_{part}" for n in range(26, 32) for part in ("answer", "amount")),
    "line_34_answer",
    "line_36_answer",
    "line_36_payment",
    "line_43_answer",
    "line_43_circumstances",
)

LIST_KEYS = ("line_3_rows", "spouse_vehicles", "spouse_loans", "line_43_circumstances")

PER_DEBT_KEYS = (
    "payments_left",
    "payment_changes",
    "total_60_months",
    "taxes_or_insurance",
    "necessary_for_support",
    "cure",
)

MAX_ROWS = 10
