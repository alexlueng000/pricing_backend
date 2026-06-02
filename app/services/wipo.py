import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.wipo import (
    WipoBaseEntity,
    WipoCountryTreatyStatus,
    WipoDataSource,
    WipoDataSourceHistory,
    WipoDetectionResult,
    WipoPctTimeLimit,
    WipoSourceVersion,
)
from app.repositories.wipo import (
    WipoBaseEntityRepository,
    WipoCountryTreatyStatusRepository,
    WipoDataSourceHistoryRepository,
    WipoDataSourceRepository,
    WipoDetectionResultRepository,
    WipoPctTimeLimitRepository,
    WipoSourceVersionRepository,
)

FIXED_WIPO_SOURCES = [
    {
        "source_code": "wipo_pct_paris_wto_membership",
        "source_name": "WIPO PCT / Paris 成员资格",
        "official_url": "https://www.wipo.int/zh/web/pct-system/paris_wto_pct",
    },
    {
        "source_code": "wipo_pct_time_limits",
        "source_name": "WIPO PCT 进入国家阶段期限",
        "official_url": "https://www.wipo.int/zh/web/pct-system/texts/time_limits",
    },
]

SECONDS_PER_MONTH = 30 * 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 15
KNOWN_COUNTRIES = {
    "US": {"zh": "美国", "en": "United States of America", "data_type": "country", "aliases": ["美国", "United States", "US", "USA"]},
    "EP": {"zh": "欧洲专利局", "en": "European Patent Office", "data_type": "organization", "aliases": ["欧洲专利局", "European Patent Office", "EPO"]},
    "EM": {"zh": "欧盟知识产权局", "en": "European Union Intellectual Property Office", "data_type": "organization", "aliases": ["欧盟知识产权局", "European Union Intellectual Property Office", "EUIPO"]},
    "EU": {"zh": "欧盟", "en": "European Union", "data_type": "region", "aliases": ["欧盟", "European Union", "EU"]},
    "HK": {"zh": "中国香港", "en": "Hong Kong, China", "data_type": "special_jurisdiction", "aliases": ["香港", "Hong Kong", "HK"]},
    "MO": {"zh": "中国澳门", "en": "Macao, China", "data_type": "special_jurisdiction", "aliases": ["澳门", "Macao", "Macau", "MO"]},
    "TW": {"zh": "中国台湾", "en": "Taiwan, China", "data_type": "special_jurisdiction", "aliases": ["台湾", "Taiwan", "TW"]},
    "JP": {"zh": "日本", "en": "Japan", "data_type": "country", "aliases": ["日本", "Japan", "JP"]},
    "KR": {"zh": "韩国", "en": "Republic of Korea", "data_type": "country", "aliases": ["韩国", "Republic of Korea", "Korea", "KR"]},
}


class WipoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sources = WipoDataSourceRepository(db)
        self.histories = WipoDataSourceHistoryRepository(db)
        self.detections = WipoDetectionResultRepository(db)
        self.versions = WipoSourceVersionRepository(db)
        self.base_entities = WipoBaseEntityRepository(db)
        self.treaties = WipoCountryTreatyStatusRepository(db)
        self.time_limits = WipoPctTimeLimitRepository(db)

    def list_sources(self) -> list[dict[str, object]]:
        self.ensure_fixed_sources()
        return [self._source_with_reminder(source) for source in self.sources.list_items()]

    def detect_source(self, source_code: str, *, operated_by: int) -> dict[str, object] | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        if source_code not in {item["source_code"] for item in FIXED_WIPO_SOURCES}:
            raise ValueError("仅允许检测固定 WIPO 官方数据源")

        now = datetime.now(timezone.utc)
        result = self._detect_source_result(source, operated_by=operated_by, detected_at=now)
        source.last_checked_at = now
        source.check_status = result.status
        history = WipoDataSourceHistory(
            source_id=source.id,
            version=source.current_version,
            source_status_date=result.source_status_date,
            checked_at=now,
            published_at=None,
            status=result.status,
            operated_by=operated_by,
            summary=result.validation_summary or result.failure_reason,
        )
        self.histories.add(history)
        self.db.commit()
        self.db.refresh(source)
        return self._source_with_reminder(source)

    def detect_source_with_result(self, source_code: str, *, operated_by: int) -> WipoDetectionResult | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        if source_code not in {item["source_code"] for item in FIXED_WIPO_SOURCES}:
            raise ValueError("仅允许检测固定 WIPO 官方数据源")
        now = datetime.now(timezone.utc)
        result = self._detect_source_result(source, operated_by=operated_by, detected_at=now)
        source.last_checked_at = now
        source.check_status = result.status
        self.histories.add(
            WipoDataSourceHistory(
                source_id=source.id,
                version=source.current_version,
                source_status_date=result.source_status_date,
                checked_at=now,
                status=result.status,
                operated_by=operated_by,
                summary=result.validation_summary or result.failure_reason,
            )
        )
        self.db.commit()
        self.db.refresh(result)
        return result

    def publish_detection(self, source_code: str, detection_id: int, *, operated_by: int) -> WipoDataSource | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        detection = self.detections.get(detection_id)
        if detection is None or detection.source_id != source.id:
            return None
        if detection.status != "ready_for_review":
            raise ValueError("只有检测成功并通过基础校验的结果才能发布")
        if detection.published_at is not None:
            raise ValueError("该检测结果已发布")

        now = datetime.now(timezone.utc)
        next_version = next_wipo_version(source.current_version)
        payload = json.loads(detection.parsed_payload or "{}")
        source_version = self.versions.add(
            WipoSourceVersion(
                source_id=source.id,
                version_no=next_version,
                source_url=source.source_url or source.official_url,
                source_status_date=detection.source_status_date,
                fetched_at=detection.detected_at,
                published_at=now,
                published_by=operated_by,
                raw_snapshot=detection.raw_snapshot,
                parsed_snapshot=detection.parsed_payload,
                change_summary=detection.validation_summary,
            )
        )
        self._apply_payload(
            source.source_code,
            payload,
            version=next_version,
            source_status_date=detection.source_status_date,
            source_version_id=source_version.id,
        )
        source.current_version = next_version
        source.current_version_id = source_version.id
        source.source_status_date = detection.source_status_date
        source.last_status_date = detection.source_status_date
        source.last_checked_at = detection.detected_at
        source.last_published_at = now
        source.check_status = "published"
        detection.published_at = now
        detection.published_by = operated_by
        self.histories.add(
            WipoDataSourceHistory(
                source_id=source.id,
                version=next_version,
                source_status_date=detection.source_status_date,
                checked_at=detection.detected_at,
                published_at=now,
                status="published",
                operated_by=operated_by,
                summary=detection.validation_summary,
            )
        )
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_source_histories(self, source_code: str) -> list[WipoDataSourceHistory] | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        return self.histories.list_for_source(source.id)

    def list_detection_results(self, source_code: str) -> list[WipoDetectionResult] | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        return self.detections.list_for_source(source.id)

    def list_source_versions(self, source_code: str) -> list[WipoSourceVersion] | None:
        self.ensure_fixed_sources()
        source = self.sources.get_by_code(source_code)
        if source is None:
            return None
        return self.versions.list_for_source(source.id)

    def list_base_entities(self) -> list[WipoBaseEntity]:
        self.ensure_reference_data()
        return self.base_entities.list_items()

    def list_treaty_statuses(self) -> list[WipoCountryTreatyStatus]:
        self.ensure_reference_data()
        return self.treaties.list_items()

    def list_time_limits(self) -> list[WipoPctTimeLimit]:
        self.ensure_reference_data()
        return self.time_limits.list_items()

    def ensure_fixed_sources(self) -> None:
        changed = False
        for item in FIXED_WIPO_SOURCES:
            source = self.sources.get_by_code(item["source_code"])
            if source is None:
                self.sources.add(
                    WipoDataSource(
                        source_code=item["source_code"],
                        source_key=item["source_code"],
                        source_name=item["source_name"],
                        official_url=item["official_url"],
                        source_url=item["official_url"],
                        source_type="wipo_official",
                        current_version="V0",
                        check_status="never_checked",
                        is_active=True,
                    )
                )
                changed = True
            else:
                source.source_key = item["source_code"]
                source.source_name = item["source_name"]
                source.official_url = item["official_url"]
                source.source_url = item["official_url"]
                source.source_type = "wipo_official"
                source.is_active = True
        if changed:
            self.db.commit()

    def _detect_source_result(self, source: WipoDataSource, *, operated_by: int, detected_at: datetime) -> WipoDetectionResult:
        try:
            html = fetch_whitelisted_url(source.official_url)
            parsed = parse_wipo_html(source.source_code, html)
            status = "ready_for_review" if parsed["is_valid"] else "failed"
            result = WipoDetectionResult(
                source_id=source.id,
                detected_at=detected_at,
                status=status,
                failure_reason=None if parsed["is_valid"] else parsed["validation_summary"],
                source_status_date=parse_iso_date(str(parsed["source_status_date"])) if parsed["source_status_date"] else None,
                parsed_record_count=len(parsed["records"]),
                validation_summary=parsed["validation_summary"],
                raw_snapshot=html,
                parsed_payload=json.dumps(parsed, ensure_ascii=False),
                created_by=operated_by,
            )
        except Exception as exc:
            result = WipoDetectionResult(
                source_id=source.id,
                detected_at=detected_at,
                status="failed",
                failure_reason=str(exc),
                source_status_date=None,
                parsed_record_count=0,
                validation_summary="检测失败，请查看失败原因。",
                raw_snapshot=None,
                parsed_payload=None,
                created_by=operated_by,
            )
        self.detections.add(result)
        return result

    def _apply_payload(
        self,
        source_code: str,
        payload: dict[str, object],
        *,
        version: str,
        source_status_date: date | None,
        source_version_id: int,
    ) -> None:
        records = payload.get("records")
        if not isinstance(records, list):
            return
        if source_code == "wipo_pct_paris_wto_membership":
            for record in records:
                if isinstance(record, dict):
                    self._upsert_treaty_record(record, version=version, source_status_date=source_status_date, source_version_id=source_version_id)
        if source_code == "wipo_pct_time_limits":
            for record in records:
                if isinstance(record, dict):
                    self._upsert_time_limit_record(record, version=version, source_status_date=source_status_date, source_version_id=source_version_id)

    def _upsert_treaty_record(self, record: dict[str, object], *, version: str, source_status_date: date | None, source_version_id: int) -> None:
        country_code = record.get("country_code")
        if not isinstance(country_code, str):
            return
        existing = self.db.scalar(select(WipoCountryTreatyStatus).where(WipoCountryTreatyStatus.country_code == country_code))
        values = {
            "name_zh": str(record.get("name_zh") or country_code),
            "name_en": str(record.get("name_en") or ""),
            "is_pct_member": bool(record.get("is_pct_member")),
            "is_paris_member": bool(record.get("is_paris_member")),
            "is_wto_member": existing.is_wto_member if existing else False,
            "source_url": str(record.get("source_url") or FIXED_WIPO_SOURCES[0]["official_url"]),
            "source_status_date": source_status_date,
            "version": version,
        }
        if existing is None:
            self.treaties.add(WipoCountryTreatyStatus(country_code=country_code, **values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self._upsert_base_entity(record, source_version_id=source_version_id, note="成员资格数据来自已发布WIPO来源版本。")

    def _upsert_time_limit_record(self, record: dict[str, object], *, version: str, source_status_date: date | None, source_version_id: int) -> None:
        country_code = record.get("country_code")
        months = record.get("pct_entry_deadline_first_chapter")
        if not isinstance(country_code, str) or not isinstance(months, int):
            return
        existing = self.db.scalar(select(WipoPctTimeLimit).where(WipoPctTimeLimit.country_code == country_code))
        values = {
            "pct_entry_deadline_first_chapter": months,
            "source_url": str(record.get("source_url") or FIXED_WIPO_SOURCES[1]["official_url"]),
            "source_status_date": source_status_date,
            "version": version,
        }
        if existing is None:
            self.time_limits.add(WipoPctTimeLimit(country_code=country_code, **values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self._upsert_base_entity(record, source_version_id=source_version_id, note="PCT第一章期限数据来自已发布WIPO来源版本。")

    def _upsert_base_entity(self, record: dict[str, object], *, source_version_id: int, note: str) -> None:
        code = record.get("country_code")
        if not isinstance(code, str):
            return
        existing = self.base_entities.get_by_code(code)
        record_note = record.get("note")
        combined_note = note
        if isinstance(record_note, str) and record_note.strip():
            combined_note = f"{note} {record_note.strip()}"
        values = {
            "name_zh": str(record.get("name_zh") or code),
            "name_en": str(record.get("name_en") or ""),
            "data_type": str(record.get("data_type") or infer_data_type(code)),
            "is_pct_member": bool(record.get("is_pct_member")) if "is_pct_member" in record else existing.is_pct_member if existing else False,
            "is_paris_member": bool(record.get("is_paris_member")) if "is_paris_member" in record else existing.is_paris_member if existing else False,
            "is_wto_member": bool(record.get("is_wto_member")) if "is_wto_member" in record else existing.is_wto_member if existing else False,
            "pct_entry_deadline_chapter_1": record.get("pct_entry_deadline_first_chapter") if isinstance(record.get("pct_entry_deadline_first_chapter"), int) else existing.pct_entry_deadline_chapter_1 if existing else None,
            "source_version_id": source_version_id,
            "note": combined_note,
            "is_active": True,
        }
        if existing is None:
            self.base_entities.add(WipoBaseEntity(code=code, **values))
            return
        for key, value in values.items():
            setattr(existing, key, value)

    def ensure_reference_data(self) -> None:
        self.ensure_fixed_sources()
        if not self.treaties.list_items():
            for item in [
                ("US", "美国", "United States of America", True, True, True),
                ("EP", "欧洲专利局", "European Patent Office", True, True, False),
                ("EM", "欧盟知识产权局", "European Union Intellectual Property Office", False, True, False),
                ("JP", "日本", "Japan", True, True, True),
                ("KR", "韩国", "Republic of Korea", True, True, True),
            ]:
                self.treaties.add(
                    WipoCountryTreatyStatus(
                        country_code=item[0],
                        name_zh=item[1],
                        name_en=item[2],
                        is_pct_member=item[3],
                        is_paris_member=item[4],
                        is_wto_member=item[5],
                        source_url=FIXED_WIPO_SOURCES[0]["official_url"],
                        version="seed",
                    )
                )
        if not self.time_limits.list_items():
            for country_code, months in [("US", 30), ("EP", 31), ("JP", 30), ("KR", 31)]:
                self.time_limits.add(
                    WipoPctTimeLimit(
                        country_code=country_code,
                        pct_entry_deadline_first_chapter=months,
                        source_url=FIXED_WIPO_SOURCES[1]["official_url"],
                        version="seed",
                    )
                )
        if not self.base_entities.list_items():
            for code, defaults in KNOWN_COUNTRIES.items():
                self.base_entities.add(
                    WipoBaseEntity(
                        code=code,
                        name_zh=str(defaults["zh"]),
                        name_en=str(defaults["en"]),
                        data_type=str(defaults["data_type"]),
                        is_pct_member=code in {"US", "EP", "JP", "KR"},
                        is_paris_member=code in {"US", "EP", "EM", "JP", "KR"},
                        is_wto_member=code in {"US", "JP", "KR"},
                        pct_entry_deadline_chapter_1={"US": 30, "EP": 31, "JP": 30, "KR": 31}.get(code),
                        source_version_id=None,
                        note="MVP种子数据；code来自WIPO基础数据，不允许前端手填。",
                        is_active=True,
                    )
                )
        self.db.commit()

    @staticmethod
    def _source_with_reminder(source: WipoDataSource) -> dict[str, object]:
        level, label = reminder_for_checked_at(source.last_checked_at)
        return {
            "id": source.id,
            "source_code": source.source_code,
            "source_key": source.source_key or source.source_code,
            "source_name": source.source_name,
            "official_url": source.official_url,
            "source_url": source.source_url or source.official_url,
            "source_type": source.source_type,
            "current_version": source.current_version,
            "current_version_id": source.current_version_id,
            "source_status_date": source.source_status_date,
            "last_status_date": source.last_status_date or source.source_status_date,
            "last_checked_at": source.last_checked_at,
            "last_published_at": source.last_published_at,
            "check_status": source.check_status,
            "is_active": source.is_active,
            "created_at": source.created_at,
            "updated_at": source.updated_at,
            "reminder_level": level,
            "reminder_label": label,
        }


def reminder_for_checked_at(last_checked_at: datetime | None) -> tuple[str, str]:
    if last_checked_at is None:
        return "red", "需要检测"
    checked_at = last_checked_at
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = (datetime.now(timezone.utc) - checked_at).total_seconds()
    if elapsed_seconds < SECONDS_PER_MONTH:
        return "green", "正常"
    if elapsed_seconds <= 3 * SECONDS_PER_MONTH:
        return "yellow", "建议检测"
    return "red", "需要检测"


def fetch_whitelisted_url(url: str) -> str:
    allowed_urls = {item["official_url"] for item in FIXED_WIPO_SOURCES}
    if url not in allowed_urls:
        raise ValueError("仅允许抓取固定 WIPO 白名单 URL")
    request = Request(url, headers={"User-Agent": "PatentQuoteSystem/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"官方页面返回 HTTP {status}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise ValueError(f"官方页面返回 HTTP {exc.code}") from exc
    except URLError as exc:
        raise ValueError(f"无法访问官方页面：{exc.reason}") from exc
    except TimeoutError as exc:
        raise ValueError("访问官方页面超时") from exc


class WipoTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            cell = normalize_space(" ".join(self._current_cell))
            self._current_row.append(cell)
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            if any(cell for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        self.text_parts.append(text)
        if self._current_cell is not None:
            self._current_cell.append(text)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


def parse_wipo_html(source_code: str, html: str) -> dict[str, object]:
    if len(html) < 500:
        return parsed_result([], None, "抓取内容过短，未通过基础校验。")
    parser = WipoTableParser()
    parser.feed(html)
    source_status_date = extract_source_status_date(parser.text)
    table_rows = [row for table in parser.tables for row in table]
    if source_code == "wipo_pct_paris_wto_membership":
        records, validation = parse_paris_wto_pct_records(parser.tables, parser.text)
        is_valid = validation["is_valid"]
        summary = validation["summary"]
        return parsed_result(records, source_status_date, summary, is_valid=is_valid)
    if source_code == "wipo_pct_time_limits":
        records, validation = parse_pct_time_limit_chapter_1_records(parser.tables, parser.text)
        return parsed_result(records, source_status_date, validation["summary"], is_valid=validation["is_valid"])
    else:
        records = parse_membership_records(source_code, table_rows)
    if not table_rows:
        return parsed_result(records, source_status_date, "未解析到表格数据，未通过基础校验。")
    if not records:
        return parsed_result(records, source_status_date, "已抓取页面，但未识别到欧美日韩相关结构化记录，请人工复核页面结构。")
    validation = f"已抓取官方页面，解析表格行 {len(table_rows)} 行，识别记录 {len(records)} 条。"
    return parsed_result(records, source_status_date, validation, is_valid=True)


def parse_paris_wto_pct_records(tables: list[list[list[str]]], page_text: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    footnotes = extract_footnotes(page_text)
    expected_counts = extract_membership_counts(page_text)
    candidate_rows = best_membership_table_rows(tables)
    records: list[dict[str, object]] = []
    for row in candidate_rows:
        record = parse_membership_table_row(row, footnotes)
        if record is not None:
            records.append(record)

    if not records:
        return [], {"is_valid": False, "summary": "未识别到成员资格表格数据。"}

    actual_counts = {
        "pct": sum(1 for record in records if record["is_pct_member"]),
        "paris": sum(1 for record in records if record["is_paris_member"]),
    }
    mismatches = []
    for key, expected in expected_counts.items():
        if expected is not None and actual_counts[key] != expected:
            labels = {"pct": "PCT", "paris": "巴黎公约"}
            mismatches.append(f"{labels[key]}页面统计{expected}，实际解析{actual_counts[key]}")
    if mismatches:
        return records, {
            "is_valid": False,
            "summary": f"成员数量校验未通过：{'；'.join(mismatches)}。",
        }
    expected_text = "，".join(
        f"{label}{expected_counts[key]}"
        for key, label in [("pct", "PCT"), ("paris", "巴黎公约")]
        if expected_counts[key] is not None
    )
    return records, {
        "is_valid": True,
        "summary": f"已解析成员资格记录{len(records)}条；成员数量校验通过（{expected_text}）。",
    }


def parse_pct_time_limit_chapter_1_records(tables: list[list[list[str]]], page_text: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    footnotes = extract_footnotes(page_text)
    table, chapter_1_index = best_pct_time_limit_table(tables)
    if not table or chapter_1_index is None:
        return [], {"is_valid": False, "summary": "未识别到PCT进入国家阶段期限第I章表格。"}

    records: list[dict[str, object]] = []
    for row in table:
        record = parse_pct_time_limit_chapter_1_row(row, chapter_1_index, footnotes)
        if record is not None:
            records.append(record)

    if not records:
        return [], {"is_valid": False, "summary": "未识别到第I章进入国家阶段期限数据。"}
    return records, {
        "is_valid": True,
        "summary": f"已解析PCT第I章进入国家阶段期限记录{len(records)}条；第II章未解析、未展示、未参与计算。",
    }


def best_pct_time_limit_table(tables: list[list[list[str]]]) -> tuple[list[list[str]], int | None]:
    best_table: list[list[str]] = []
    best_index: int | None = None
    best_count = 0
    for table in tables:
        header_index = None
        chapter_1_index = None
        for index, row in enumerate(table[:5]):
            normalized_cells = [normalize_space(cell) for cell in row]
            for cell_index, cell in enumerate(normalized_cells):
                if is_chapter_1_header(cell):
                    header_index = index
                    chapter_1_index = cell_index
                    break
            if chapter_1_index is not None:
                break
        if chapter_1_index is None:
            continue
        data_rows = table[(header_index or 0) + 1:]
        record_count = sum(1 for row in data_rows if parse_pct_time_limit_chapter_1_row(row, chapter_1_index, {}) is not None)
        if record_count > best_count:
            best_table = data_rows
            best_index = chapter_1_index
            best_count = record_count
    return best_table, best_index


def parse_pct_time_limit_chapter_1_row(row: list[str], chapter_1_index: int, footnotes: dict[str, str]) -> dict[str, object] | None:
    if len(row) < 3:
        return None
    code_cell = normalize_space(row[0])
    code_match = match_wipo_code_cell(code_cell)
    if not code_match:
        return None
    deadline_index = chapter_1_index
    if len(row) == 4 and chapter_1_index == 1:
        deadline_index = 2
    if len(row) <= deadline_index:
        return None
    chapter_1_cell = normalize_space(row[deadline_index])
    months = extract_deadline_months(chapter_1_cell)
    if months is None:
        return None
    code = code_match.group(1)
    name_cell = normalize_space(row[1])
    note_numbers = sorted(set(
        note_numbers_from_text(code_cell)
        + note_numbers_from_text(name_cell)
        + note_numbers_from_text(chapter_1_cell)
    ))
    note = "；".join(
        f"{number}. {footnotes[number]}"
        for number in note_numbers
        if number in footnotes
    )
    return {
        "country_code": code,
        "name_zh": clean_note_numbers(name_cell),
        "name_en": None,
        "data_type": infer_data_type(code),
        "pct_entry_deadline_first_chapter": months,
        "source_url": source_url_for_code("wipo_pct_time_limits"),
        "note": note or "PCT第I章进入国家阶段期限仅作为基础数据展示和备注维护，不在本阶段做复杂期限计算。",
        "raw": " | ".join(row)[:500],
    }


def is_chapter_1_header(value: str) -> bool:
    normalized = normalize_space(value).casefold()
    return (
        bool(re.search(r"chapter\s*i(?!i)", normalized))
        or "第i章" in normalized
        or "第 i 章" in normalized
        or "第一章" in normalized
    )


def best_membership_table_rows(tables: list[list[list[str]]]) -> list[list[str]]:
    best: list[list[str]] = []
    for table in tables:
        rows = [row for row in table if row]
        code_rows = [row for row in rows if row and match_wipo_code_cell(normalize_space(row[0]))]
        if len(code_rows) > len(best):
            best = code_rows
    return best


def parse_membership_table_row(row: list[str], footnotes: dict[str, str]) -> dict[str, object] | None:
    if len(row) < 4:
        return None
    code_cell = normalize_space(row[0])
    code_match = match_wipo_code_cell(code_cell)
    if not code_match:
        return None
    code = code_match.group(1)
    code_note_numbers = note_numbers_from_text(code_cell)
    name_zh = normalize_space(row[1])
    pct_cell = normalize_space(row[2])
    paris_cell = normalize_space(row[3])
    note_numbers = sorted(set(
        code_note_numbers
        + note_numbers_from_text(name_zh)
        + note_numbers_from_text(pct_cell)
        + note_numbers_from_text(paris_cell)
    ))
    note = "；".join(
        f"{number}. {footnotes[number]}"
        for number in note_numbers
        if number in footnotes
    )
    return {
        "country_code": code,
        "name_zh": clean_note_numbers(name_zh),
        "name_en": None,
        "data_type": infer_data_type(code),
        "is_pct_member": membership_marker_is_true(pct_cell),
        "is_paris_member": membership_marker_is_true(paris_cell),
        "source_url": source_url_for_code("wipo_pct_paris_wto_membership"),
        "note": note or None,
        "raw": " | ".join(row[:4])[:500],
    }


def membership_marker_is_true(value: str) -> bool:
    return normalize_space(value).upper().startswith("X")


def match_wipo_code_cell(value: str) -> re.Match[str] | None:
    return re.fullmatch(r"([A-Z]{2})(?:\s*(\d{1,2}))?", normalize_space(value))


def note_numbers_from_text(value: str) -> list[str]:
    return re.findall(r"(?<!\d)([1-9]\d?)(?!\d)", value)


def clean_note_numbers(value: str) -> str:
    return normalize_space(re.sub(r"(?<!\d)[1-9]\d?(?!\d)", "", value))


def infer_data_type(code: str) -> str:
    if code == "EU":
        return "region"
    if code in {"AP", "EA", "EP", "OA"}:
        return "regional_office"
    if code in {"EM"}:
        return "organization"
    if code in {"HK", "MO", "TW"}:
        return "special_jurisdiction"
    return "country"


def extract_membership_counts(text: str) -> dict[str, int | None]:
    def count_after(label: str) -> int | None:
        match = re.search(rf"{label}\s*\d*\s*\(?\s*(\d{{2,3}})\s*\)?", text)
        return int(match.group(1)) if match else None

    return {
        "pct": count_after("专利合作条约"),
        "paris": count_after("巴黎公约"),
    }

def extract_footnotes(text: str) -> dict[str, str]:
    notes: dict[str, str] = {}
    tail_match = re.search(r"\s1\.\s+(.+?)(?:\s隐藏的|\s页面正文|\shttps://|$)", text)
    if not tail_match:
        return notes
    tail = f"1. {tail_match.group(1)}"
    for match in re.finditer(r"(?<!\d)([1-9]\d?)\.\s+(.*?)(?=\s+[1-9]\d?\.\s+|$)", tail):
        notes[match.group(1)] = normalize_space(match.group(2))
    return notes


def parsed_result(
    records: list[dict[str, object]],
    source_status_date: date | None,
    validation_summary: str,
    *,
    is_valid: bool = False,
) -> dict[str, object]:
    return {
        "records": records,
        "source_status_date": source_status_date.isoformat() if source_status_date else None,
        "validation_summary": validation_summary,
        "is_valid": is_valid,
    }


def parse_membership_records(source_code: str, rows: list[list[str]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for country_code, data in KNOWN_COUNTRIES.items():
        matched_text = first_matching_row_text(rows, data["aliases"])
        if not matched_text:
            continue
        is_pct = has_positive_marker(matched_text, ["pct", "专利合作条约"])
        is_paris = has_positive_marker(matched_text, ["paris", "巴黎"])
        records.append(
            {
                "country_code": country_code,
                "name_zh": data["zh"],
                "name_en": data["en"],
                "is_pct_member": is_pct,
                "is_paris_member": is_paris,
                "source_url": source_url_for_code(source_code),
                "raw": matched_text[:500],
            }
        )
    return records


def parse_time_limit_records(rows: list[list[str]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for country_code, data in KNOWN_COUNTRIES.items():
        matched_text = first_matching_row_text(rows, data["aliases"])
        if not matched_text:
            continue
        months = extract_deadline_months(matched_text)
        if months is None:
            continue
        records.append(
            {
                "country_code": country_code,
                "pct_entry_deadline_first_chapter": months,
                "source_url": source_url_for_code("wipo_pct_time_limits"),
                "raw": matched_text[:500],
            }
        )
    return records


def first_matching_row_text(rows: list[list[str]], aliases: list[str]) -> str | None:
    for row in rows:
        text = normalize_space(" ".join(row))
        lowered = text.casefold()
        if any(alias.casefold() in lowered for alias in aliases):
            return text
    return None


def has_positive_marker(text: str, markers: list[str]) -> bool:
    lowered = text.casefold()
    if not any(marker.casefold() in lowered for marker in markers):
        return False
    negative_markers = ["not a member", "不是", "否", "no"]
    return not any(marker in lowered for marker in negative_markers)


def extract_status_date(text: str) -> date | None:
    patterns = [
        r"(20\d{2}|19\d{2})[-./年](\d{1,2})[-./月](\d{1,2})日?",
        r"(\d{1,2})[-./](\d{1,2})[-./](20\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            if len(match.group(1)) == 4:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            continue
    return None


def extract_source_status_date(text: str) -> date | None:
    for match in re.finditer(r"(.{0,20})(20\d{2}|19\d{2})[-./年](\d{1,2})[-./月](\d{1,2})日?(.{0,20})", text):
        context = f"{match.group(1)}{match.group(5)}"
        if "状态" not in context and "status" not in context.casefold():
            continue
        if "不是" in context or "非" in context:
            continue
        try:
            return date(int(match.group(2)), int(match.group(3)), int(match.group(4)))
        except ValueError:
            continue
    for match in re.finditer(r"(.{0,20})(\d{1,2})[-./](\d{1,2})[-./](20\d{2}|19\d{2})(.{0,20})", text):
        context = f"{match.group(1)}{match.group(5)}"
        if "状态" not in context and "status" not in context.casefold():
            continue
        if "不是" in context or "非" in context:
            continue
        try:
            return date(int(match.group(4)), int(match.group(3)), int(match.group(2)))
        except ValueError:
            continue
    return None


def extract_join_date(text: str) -> str | None:
    parsed = extract_status_date(text)
    return parsed.isoformat() if parsed else None


def extract_any_date(text: str) -> date | None:
    parsed = extract_status_date(text)
    if parsed is not None:
        return parsed
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    match = re.search(
        r"(?P<day>\d{1,2})\s+(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<year>20\d{2}|19\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        try:
            return date(
                int(match.group("year")),
                month_names[match.group("month").casefold()],
                int(match.group("day")),
            )
        except ValueError:
            return None
    match = re.search(
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<day>\d{1,2}),?\s+(?P<year>20\d{2}|19\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        try:
            return date(
                int(match.group("year")),
                month_names[match.group("month").casefold()],
                int(match.group("day")),
            )
        except ValueError:
            return None
    return None


def extract_deadline_months(text: str) -> int | None:
    for match in re.finditer(r"(?<!\d)(\d{2})(?!\d)", text):
        months = int(match.group(1))
        if 18 <= months <= 40:
            return months
    return None


def source_url_for_code(source_code: str) -> str:
    for source in FIXED_WIPO_SOURCES:
        if source["source_code"] == source_code:
            return source["official_url"]
    return ""


def next_wipo_version(current_version: str) -> str:
    match = re.fullmatch(r"V(\d+)", current_version.strip(), flags=re.IGNORECASE)
    if not match:
        return "V1"
    return f"V{int(match.group(1)) + 1}"


def build_raw_snapshot(payload: dict[str, object]) -> str | None:
    records = payload.get("records")
    if not isinstance(records, list):
        return None
    raw_rows = []
    for record in records:
        if isinstance(record, dict) and record.get("raw"):
            raw_rows.append({"country_code": record.get("country_code"), "raw": record.get("raw")})
    return json.dumps(raw_rows, ensure_ascii=False) if raw_rows else None


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
