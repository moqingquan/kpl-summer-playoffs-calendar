#!/usr/bin/env python3
"""Generate an iOS-compatible ICS feed for the current KPL season.

The source is the public schedule endpoint used by the official KPL website.
The same UID is kept for each schedule item, so calendar clients update an
existing event when a TBD team becomes known or a score/status changes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "https://kplshop-op.timi-esports.qq.com/kplow"
SEASONS_URL = f"{API_BASE}/getSeasonAndStageAndTeamList"
SCHEDULE_URL = f"{API_BASE}/getScheduleList"
KPL_SCHEDULE_URL = "https://kpl.qq.com/#/Schedule"
DEFAULT_OUTPUT = Path(__file__).with_name("kpl-summer-playoffs.ics")
BEIJING = timezone(timedelta(hours=8))


def post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://kpl.qq.com",
            "Referer": "https://kpl.qq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("result") != 0:
        raise RuntimeError(f"KPL接口返回错误: {data.get('msg') or data.get('result')}")
    return data


def resolve_season_id(requested: str | None) -> tuple[str, str]:
    if requested:
        return requested, requested
    data = post_json(SEASONS_URL, {"seasonid": ""}).get("data", {})
    seasons = data.get("seasons", [])
    if not seasons:
        raise RuntimeError("未能从KPL官网找到可用赛季")

    # The official site marks the active season. This means the feed follows
    # the next spring/summer/annual season without a code change.
    current = next(
        (season for season in seasons if str(season.get("is_cur_season")) == "1"),
        None,
    )
    if current is None:
        now = int(datetime.now(timezone.utc).timestamp())
        active = [
            season
            for season in seasons
            if int(season.get("start_time", 0) or 0)
            <= now
            <= int(season.get("end_time", 0) or 0)
        ]
        current = max(active or seasons, key=lambda season: int(season.get("start_time", 0) or 0))

    return str(current["seasonid"]), str(current.get("season_name") or current["seasonid"])


def fetch_matches(season_id: str) -> list[dict]:
    data = post_json(
        SCHEDULE_URL,
        {"seasonid": season_id, "stageid": "", "team_id": ""},
    ).get("data", {})
    matches = []
    for item in data.get("list", []):
        if not item.get("scheduleid"):
            continue
        try:
            if int(item.get("start_timestamp", 0)) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        matches.append(item)
    if not matches:
        raise RuntimeError(f"官网没有返回 {season_id} 的赛程")
    return sorted(matches, key=lambda item: int(item["start_timestamp"]))


def ics_escape(value: object) -> str:
    text = str(value or "")
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_ical_line(line: str) -> list[str]:
    """Fold long UTF-8 lines according to RFC 5545 without splitting bytes."""
    result: list[str] = []
    current = ""
    current_bytes = 0
    for char in line:
        char_bytes = len(char.encode("utf-8"))
        if current and current_bytes + char_bytes > 72:
            result.append(current)
            current = " " + char
            current_bytes = 1 + char_bytes
        else:
            current += char
            current_bytes += char_bytes
    if current or not result:
        result.append(current)
    return result


def ical_datetime(timestamp: object) -> datetime:
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def status_label(status: object) -> str:
    try:
        code = int(status)
    except (TypeError, ValueError):
        code = 1
    return {1: "未开始", 2: "已取消", 3: "进行中", 4: "已结束"}.get(code, "未知")


def status_code(status: object) -> int:
    try:
        return int(status)
    except (TypeError, ValueError):
        return 1


def team_name(item: dict, side: str) -> str:
    name = str(item.get(f"team_{side}_name") or "待定").strip()
    return name if name and name not in {"-", "暂无"} else "待定"


def stage_name(item: dict) -> str:
    return str(item.get("stage_name") or item.get("stageid") or "KPL赛程").strip()


def make_description(item: dict, season_name: str) -> str:
    current_status = status_code(item.get("schedule_status", 1))
    status = status_label(current_status)
    score_a = item.get("team_a_score", 0)
    score_b = item.get("team_b_score", 0)
    location = item.get("location_name") or "待定"
    fmt = item.get("competition_format") or (
        f"BO{item['bo_total']}" if item.get("bo_total") else "待定"
    )
    return "\n".join(
        [
            season_name,
            f"阶段：{stage_name(item)}",
            f"赛制：{fmt}",
            f"状态：{status}",
            f"比分：{score_a} : {score_b}" if current_status != 1 else "比分：未开始",
            f"场馆/城市：{location}",
            "本日历由KPL官网公开赛程自动更新；对阵中的“待定”会在赛果确认后替换。",
            f"官网：{KPL_SCHEDULE_URL}",
        ]
    )


def generate_ics(matches: list[dict], season_name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # A monotonically increasing daily revision makes iOS refresh changed
    # titles/scores even when the feed URL itself is cached briefly.
    sequence = str(int(time.time() // 86400))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KPL Calendar//KPL Schedule//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(season_name)}｜KPL完整赛程",
        f"X-WR-CALDESC:{ics_escape(season_name)}全部阶段动态赛程（每日更新）",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]
    for item in matches:
        start = ical_datetime(item["start_timestamp"])
        end = start + timedelta(hours=4)
        a_name = team_name(item, "a")
        b_name = team_name(item, "b")
        schedule_id = str(item["scheduleid"])
        current_status = status_code(item.get("schedule_status", 1))
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{ics_escape(schedule_id)}@kpl-calendar.local",
                f"DTSTAMP:{now}",
                f"SEQUENCE:{sequence}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{ics_escape('KPL｜' + a_name + ' vs ' + b_name)}",
                f"DESCRIPTION:{ics_escape(make_description(item, season_name))}",
                f"LOCATION:{ics_escape(item.get('location_name') or '待定')}",
                f"STATUS:{'CANCELLED' if current_status == 2 else 'CONFIRMED'}",
                "TRANSP:OPAQUE",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in fold_ical_line(line)) + "\r\n"


def write_calendar(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="更新当前KPL赛季全部阶段的iOS日历订阅文件")
    parser.add_argument(
        "--season-id",
        default="",
        help="KPL赛季ID；留空则自动跟随官网当前赛季",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出ICS路径")
    args = parser.parse_args()
    try:
        season_id, season_name = resolve_season_id(args.season_id)
        matches = fetch_matches(season_id)
        content = generate_ics(matches, season_name)
        write_calendar(args.output, content)
        print(f"已更新: {args.output}")
        print(f"赛季: {season_name} ({season_id}); 全部赛程: {len(matches)} 场")
        return 0
    except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError, OSError, KeyError) as exc:
        print(f"更新失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

