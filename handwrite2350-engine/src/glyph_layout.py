import csv
import json
import os
from pathlib import Path
from statistics import median

from glyph_classify import classify_glyph


DEFAULT_CONFIG_PATH = Path("config/glyph_layout.json")
OUTPUTS_DIR = Path(os.environ.get("HANDWRITE_OUTPUTS_DIR", "/app/outputs"))
LAYOUT_REPORT_PATH = OUTPUTS_DIR / "glyph_layout_report.csv"
LAYOUT_SUMMARY_PATH = OUTPUTS_DIR / "glyph_layout_summary.txt"


FALLBACK_CONFIG = {
    "version": 1,
    "global": {
        "glyph_size": 512,
        "default_center_x": 256,
        "default_center_y": 270,
        "default_width": 230,
        "default_height": 300,
        "outlier_low_ratio": 0.75,
        "outlier_high_ratio": 1.25,
    },
    "zones": {
        "default": {
            "anchor": "default",
            "target_center_x": 256,
            "target_center_y": 270,
            "target_width": 230,
            "target_height": 300,
        }
    },
    "groups": {
        "default": {
            "zone": "default",
            "scale_policy": "none",
        }
    },
    "overrides": {},
}


def load_glyph_layout_config(path=DEFAULT_CONFIG_PATH):
    config_path = Path(path)
    if not config_path.exists():
        return FALLBACK_CONFIG.copy()

    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    validate_glyph_layout_config(config)
    return config


def validate_glyph_layout_config(config):
    if not isinstance(config, dict):
        raise ValueError("glyph layout config must be a JSON object")
    for key in ["global", "zones", "groups"]:
        if key not in config or not isinstance(config[key], dict):
            raise ValueError(f"glyph layout config missing object: {key}")

    for group_name, group_rule in config["groups"].items():
        zone_name = group_rule.get("zone")
        if zone_name not in config["zones"]:
            raise ValueError(
                f"glyph layout group '{group_name}' references missing zone '{zone_name}'"
            )


def percentile(values, ratio):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * ratio))
    return float(sorted_values[index])


def compute_group_statistics(metrics_rows):
    grouped = {}
    for row in metrics_rows:
        if not row.get("ok", True):
            continue
        grouped.setdefault(row.get("group", "default"), []).append(row)

    stats = {}
    for group, rows in grouped.items():
        widths = [row["bbox_width"] for row in rows if row.get("bbox_width")]
        heights = [row["bbox_height"] for row in rows if row.get("bbox_height")]
        centers_x = [row["center_x"] for row in rows if row.get("center_x") is not None]
        centers_y = [row["center_y"] for row in rows if row.get("center_y") is not None]
        if not widths or not heights:
            continue
        stats[group] = {
            "count": len(rows),
            "median_width": float(median(widths)),
            "median_height": float(median(heights)),
            "median_center_x": float(median(centers_x)) if centers_x else 0.0,
            "median_center_y": float(median(centers_y)) if centers_y else 0.0,
            "p25_width": percentile(widths, 0.25),
            "p75_width": percentile(widths, 0.75),
            "p25_height": percentile(heights, 0.25),
            "p75_height": percentile(heights, 0.75),
        }
    return stats


def get_group_for_char(char, config=None):
    config = config or FALLBACK_CONFIG
    override = config.get("overrides", {}).get(char, {})
    return override.get("group") or classify_glyph(char)


def resolve_layout_rule(char, group, config):
    config = config or FALLBACK_CONFIG
    groups = config.get("groups", {})
    zones = config.get("zones", {})
    rule = dict(groups.get(group) or groups.get("default") or {})
    missing_config_group = group not in groups
    zone_name = rule.get("zone", "default")
    zone = dict(zones.get(zone_name) or zones.get("default") or {})

    merged = {
        "char": char,
        "group": group,
        "zone": zone_name,
        "anchor": zone.get("anchor", zone_name),
        "missing_config_group": missing_config_group,
    }
    merged.update(zone)
    merged.update(rule)
    return merged


def _number(rule, key, default=0):
    value = rule.get(key, default)
    return float(value if value is not None else default)


def _reference_dimensions(rule, group_stats):
    reference_group = rule.get("reference_group") or rule.get("group")
    reference = group_stats.get(reference_group, {})
    return (
        float(reference.get("median_width") or _number(rule, "target_width", 1)),
        float(reference.get("median_height") or _number(rule, "target_height", 1)),
    )


def apply_adaptive_layout(metrics, group_stats, rule):
    target_width = _number(rule, "target_width", 230)
    target_height = _number(rule, "target_height", 300)
    target_center_x = _number(rule, "target_center_x", 256)
    target_center_y = _number(rule, "target_center_y", 270)

    target_width += _number(rule, "target_width_adjust", 0)
    target_height += _number(rule, "target_height_adjust", 0)
    target_center_x += _number(rule, "target_center_x_adjust", 0)
    target_center_y += _number(rule, "target_center_y_adjust", 0)

    if "target_width_ratio" in rule or "target_height_ratio" in rule:
        ref_width, ref_height = _reference_dimensions(rule, group_stats)
        if "target_width_ratio" in rule:
            target_width = ref_width * _number(rule, "target_width_ratio", 1.0)
        if "target_height_ratio" in rule:
            target_height = ref_height * _number(rule, "target_height_ratio", 1.0)

    scale_policy = rule.get("scale_policy", "none")
    outlier_detected = False
    correction_applied = False
    width_ratio = ""
    height_ratio = ""

    if scale_policy in {"group_median_clamp", "reference_group_clamp"}:
        ref_width, ref_height = _reference_dimensions(rule, group_stats)
        bbox_width = max(float(metrics.get("bbox_width", 0)), 1.0)
        bbox_height = max(float(metrics.get("bbox_height", 0)), 1.0)
        width_ratio = bbox_width / max(ref_width, 1.0)
        height_ratio = bbox_height / max(ref_height, 1.0)
        observed_ratio = max(width_ratio, height_ratio)
        min_ratio = _number(rule, "min_scale_ratio", 0.75)
        max_ratio = _number(rule, "max_scale_ratio", 1.25)
        outlier_detected = observed_ratio < min_ratio or observed_ratio > max_ratio

        if outlier_detected:
            correction_applied = True
            if observed_ratio < min_ratio:
                correction = min(min_ratio / max(observed_ratio, 0.01), 1.12)
            else:
                correction = max(max_ratio / observed_ratio, 0.90)
            target_width *= correction
            target_height *= correction

    return {
        "layout": rule.get("name") or rule.get("group", "default"),
        "target_width": int(round(target_width)),
        "target_height": int(round(target_height)),
        "target_center_x": int(round(target_center_x)),
        "target_center_y": int(round(target_center_y)),
        "zone": rule.get("zone", "default"),
        "anchor": rule.get("anchor", ""),
        "scale_policy": scale_policy,
        "outlier_detected": outlier_detected,
        "adaptive_correction_applied": correction_applied,
        "observed_width_ratio": width_ratio,
        "observed_height_ratio": height_ratio,
        "missing_config_group": rule.get("missing_config_group", False),
    }


def layout_profile_for_char(
    char,
    group,
    metrics=None,
    group_stats=None,
    config=None,
    mode="fixed",
):
    if mode != "adaptive":
        return None

    config = config or FALLBACK_CONFIG
    group = get_group_for_char(char, config)
    rule = resolve_layout_rule(char, group, config)
    adaptive = apply_adaptive_layout(metrics or {}, group_stats or {}, rule)
    return (
        adaptive["layout"],
        adaptive["target_width"],
        adaptive["target_height"],
        adaptive["target_center_x"],
        adaptive["target_center_y"],
    )


def build_layout_report_rows(metrics_rows, group_stats):
    rows = []
    for row in metrics_rows:
        group = row.get("group", "default")
        stats = group_stats.get(group, {})
        rows.append(
            {
                "index": row.get("index", ""),
                "char": row.get("char", ""),
                "unicode": row.get("unicode", ""),
                "group": group,
                "zone": row.get("zone", ""),
                "anchor": row.get("anchor", ""),
                "page": row.get("page", ""),
                "row": row.get("row", ""),
                "col": row.get("col", ""),
                "bbox_width": row.get("bbox_width", ""),
                "bbox_height": row.get("bbox_height", ""),
                "group_median_width": stats.get("median_width", ""),
                "group_median_height": stats.get("median_height", ""),
                "target_width": row.get("target_width", ""),
                "target_height": row.get("target_height", ""),
                "target_center_x": row.get("target_center_x", ""),
                "target_center_y": row.get("target_center_y", ""),
                "scale_policy": row.get("scale_policy", ""),
                "outlier_detected": row.get("outlier_detected", ""),
                "correction_applied": row.get("adaptive_correction_applied", ""),
                "missing_config_group": row.get("missing_config_group", ""),
            }
        )
    return rows


def write_glyph_layout_report(
    metrics_rows,
    group_stats,
    report_path=LAYOUT_REPORT_PATH,
    summary_path=LAYOUT_SUMMARY_PATH,
):
    rows = build_layout_report_rows(metrics_rows, group_stats)
    report_path = Path(report_path)
    summary_path = Path(summary_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "index",
        "char",
        "unicode",
        "group",
        "zone",
        "anchor",
        "page",
        "row",
        "col",
        "bbox_width",
        "bbox_height",
        "group_median_width",
        "group_median_height",
        "target_width",
        "target_height",
        "target_center_x",
        "target_center_y",
        "scale_policy",
        "outlier_detected",
        "correction_applied",
        "missing_config_group",
    ]
    with report_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)

    group_counts = {}
    for row in rows:
        group_counts[row["group"]] = group_counts.get(row["group"], 0) + 1

    outlier_count = sum(1 for row in rows if row.get("outlier_detected"))
    correction_count = sum(1 for row in rows if row.get("correction_applied"))
    default_count = group_counts.get("default", 0)
    missing_count = sum(1 for row in rows if row.get("missing_config_group"))

    lines = [
        "handwrite2350 adaptive glyph layout summary",
        "=" * 48,
        f"total glyph count: {len(rows)}",
        f"outlier glyph count: {outlier_count}",
        f"correction applied count: {correction_count}",
        f"default/fallback group count: {default_count}",
        f"missing config group count: {missing_count}",
        "",
        "group statistics:",
    ]
    for group in sorted(group_counts):
        stats = group_stats.get(group, {})
        lines.append(
            (
                f"{group}: count={group_counts[group]} "
                f"median_width={stats.get('median_width', '')} "
                f"median_height={stats.get('median_height', '')}"
            )
        )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "outlier_count": outlier_count,
        "correction_count": correction_count,
        "missing_config_group_count": missing_count,
    }
