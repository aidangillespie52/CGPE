# cgpe/models/detail.py  (only the parts you need to change)

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, List, ClassVar

from cgpe.utils.json import safe_dumps, safe_loads
from cgpe.utils.time import utc_now_iso

@dataclass
class Detail:
    card_link: str
    source: Optional[str] = None
    tcg_id: Optional[str] = None
    set_link: Optional[str] = None
    variant: Optional[str] = None

    card_name: str = ""
    card_num: str = ""
    card_img_link: Optional[str] = None

    ungraded_price: Optional[float] = None
    graded_prices_by_grade: Dict[str, Optional[float]] | None = None
    grades_1_to_10: List[Optional[float]] | None = None

    grade7_dist: Tuple[Optional[float], Optional[float]] = (None, None)
    grade8_dist: Tuple[Optional[float], Optional[float]] = (None, None)
    grade9_dist: Tuple[Optional[float], Optional[float]] = (None, None)
    grade10_dist: Tuple[Optional[float], Optional[float]] = (None, None)

    pop: Optional[dict] = None

    expected_value: Optional[float] = None
    expected_profit: Optional[float] = None

    scraped_at: Optional[str] = None

    # --- table metadata ---
    TABLE: ClassVar[str] = "card_details"
    KEY_COLUMNS: ClassVar[tuple[str, ...]] = ("card_link", "source")

    COLUMNS: ClassVar[tuple[str, ...]] = (
        "card_link",
        "tcg_id",
        "set_link",
        "card_name",
        "card_num",
        "variant",
        "source",
        "card_img_link",
        "ungraded_price",
        "grade7_mean",
        "grade7_std",
        "grade8_mean",
        "grade8_std",
        "grade9_mean",
        "grade9_std",
        "grade10_mean",
        "grade10_std",
        "pop_json",
        "graded_prices_json",
        "grades_1_to_10_json",
        "expected_value",
        "expected_profit",
        "scraped_at",
    )

    DDL_COLUMNS: ClassVar[Dict[str, str]] = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "card_link": "TEXT NOT NULL",
        "set_link": "TEXT",
        "tcg_id": "TEXT",
        "variant": "TEXT",
        "card_name": "TEXT NOT NULL",
        "card_num": "TEXT NOT NULL",
        "source": "TEXT",
        "card_img_link": "TEXT",
        "ungraded_price": "REAL",
        "grade7_mean": "REAL",
        "grade7_std": "REAL",
        "grade8_mean": "REAL",
        "grade8_std": "REAL",
        "grade9_mean": "REAL",
        "grade9_std": "REAL",
        "grade10_mean": "REAL",
        "grade10_std": "REAL",
        "pop_json": "TEXT",
        "graded_prices_json": "TEXT NOT NULL",
        "grades_1_to_10_json": "TEXT NOT NULL",
        "expected_value": "REAL",
        "expected_profit": "REAL",
        "scraped_at": "TEXT NOT NULL",
    }

    UNIQUE_CONSTRAINTS: ClassVar[list[tuple[str, ...]]] = [
        ("card_link", "source"),
    ]

    INDEXES: ClassVar[list[tuple[str, tuple[str, ...]]]] = [
        ("idx_card_details_source_num", ("source", "card_num")),
        ("idx_card_details_scraped_at", ("scraped_at",)),
    ]

    def __post_init__(self) -> None:
        if self.graded_prices_by_grade is None:
            self.graded_prices_by_grade = {}
        if self.grades_1_to_10 is None:
            self.grades_1_to_10 = []

    def to_db_row(self) -> Dict[str, Any]:
        return {
            "card_link": self.card_link,
            "tcg_id": self.tcg_id,
            "set_link": self.set_link,
            "card_name": self.card_name,
            "card_num": self.card_num,
            "variant": self.variant,
            "source": self.source,
            "card_img_link": self.card_img_link,
            "ungraded_price": self.ungraded_price,
            "grade7_mean": self.grade7_dist[0],
            "grade7_std": self.grade7_dist[1],
            "grade8_mean": self.grade8_dist[0],
            "grade8_std": self.grade8_dist[1],
            "grade9_mean": self.grade9_dist[0],
            "grade9_std": self.grade9_dist[1],
            "grade10_mean": self.grade10_dist[0],
            "grade10_std": self.grade10_dist[1],
            "pop_json": safe_dumps(self.pop),
            "graded_prices_json": safe_dumps(self.graded_prices_by_grade),
            "grades_1_to_10_json": safe_dumps(self.grades_1_to_10),
            "expected_value": self.expected_value,
            "expected_profit": self.expected_profit,
            "scraped_at": self.scraped_at or utc_now_iso(),
        }

    @classmethod
    def from_db_row(cls, r: Dict[str, Any]) -> "Detail":
        return cls(
            card_link=r["card_link"],
            tcg_id=r.get("tcg_id"),
            set_link=r.get("set_link"),
            card_name=r.get("card_name", "") or "",
            card_num=r.get("card_num", "") or "",
            variant=r.get("variant"),
            source=r.get("source"),
            card_img_link=r.get("card_img_link"),
            ungraded_price=r.get("ungraded_price"),
            grade7_dist=(r.get("grade7_mean"), r.get("grade7_std")),
            grade8_dist=(r.get("grade8_mean"), r.get("grade8_std")),
            grade9_dist=(r.get("grade9_mean"), r.get("grade9_std")),
            grade10_dist=(r.get("grade10_mean"), r.get("grade10_std")),
            pop=safe_loads(r.get("pop_json")),
            graded_prices_by_grade=safe_loads(r.get("graded_prices_json")) or {},
            grades_1_to_10=safe_loads(r.get("grades_1_to_10_json")) or [],
            expected_value=r.get("expected_value"),
            expected_profit=r.get("expected_profit"),
            scraped_at=r.get("scraped_at"),
        )

    @classmethod
    def upsert_sql(cls) -> str:
        cols = ", ".join(cls.COLUMNS)
        vals = ", ".join(f":{c}" for c in cls.COLUMNS)
        key = set(cls.KEY_COLUMNS)
        updates = ", ".join(f"{c}=excluded.{c}" for c in cls.COLUMNS if c not in key)
        return f"""
        INSERT INTO {cls.TABLE} ({cols})
        VALUES ({vals})
        ON CONFLICT({", ".join(cls.KEY_COLUMNS)}) DO UPDATE SET
            {updates}
        ;
        """.strip()