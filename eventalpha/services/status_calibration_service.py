"""Rule-based calibration for extracted event status."""

from __future__ import annotations

from dataclasses import dataclass, field

from eventalpha.schemas.event import EventStatus


ANNOUNCED_KEYWORDS = ["宣布", "公告", "发布", "决定", "声明", "称"]
HAPPENED_KEYWORDS = ["发生", "爆发", "袭击", "地震", "已造成", "登陆", "出炉"]
RUMOR_KEYWORDS = ["传闻", "据称", "尚未确认", "未经证实", "未获确认"]
WATCH_KEYWORDS = ["担忧", "市场担忧", "考虑", "预期"]
PRICED_IN_KEYWORDS = ["已提前预期", "提前反映", "市场反应平淡", "已较充分预期"]


@dataclass
class StatusCalibrationResult:
    """Calibrated status and diagnostic warnings."""

    status: EventStatus
    warnings: list[str] = field(default_factory=list)
    signal: str | None = None


class StatusCalibrationService:
    """Calibrate LLM event status using conservative text signals."""

    def calibrate_status(
        self,
        current_status: EventStatus,
        raw_title: str,
        raw_text: str,
    ) -> StatusCalibrationResult:
        """Return a calibrated status and warnings."""
        text = f"{raw_title} {raw_text}"
        warnings: list[str] = []

        has_announced = self._contains_any(text, ANNOUNCED_KEYWORDS)
        has_happened = self._contains_any(text, HAPPENED_KEYWORDS)
        has_rumor = self._contains_any(text, RUMOR_KEYWORDS)
        has_watch = self._contains_any(text, WATCH_KEYWORDS)
        has_priced_in = self._contains_any(text, PRICED_IN_KEYWORDS)

        suggested: EventStatus | None = None
        signal: str | None = None
        if has_rumor:
            suggested = "rumor"
        elif has_happened and not has_announced:
            suggested = "happened"
        elif has_announced:
            suggested = "announced"

        if has_watch:
            signal = "watch"
            warnings.append("watch signal detected; EventStatus has no watch enum")
        if has_priced_in:
            warnings.append("priced_in_or_expected signal detected")

        status: EventStatus = current_status
        if suggested and current_status != suggested:
            if self._should_correct(current_status, suggested, has_rumor):
                warnings.append(f"status calibrated: {current_status} -> {suggested}")
                status = suggested
            else:
                warnings.append(
                    f"status signal suggests {suggested}, but current status kept as {current_status}"
                )

        return StatusCalibrationResult(status=status, warnings=warnings, signal=signal)

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _should_correct(current_status: EventStatus, suggested: EventStatus, has_rumor: bool) -> bool:
        if current_status in {"unknown", "draft"}:
            return True
        if has_rumor and current_status != "rumor":
            return True
        if current_status == "announced" and suggested == "happened":
            return True
        if current_status == "happened" and suggested == "announced":
            return True
        return False
