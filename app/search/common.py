"""Shared helpers for the per-modality search modules."""

from collections import OrderedDict
from typing import Dict, List, Tuple


def source_key(payload: dict) -> Tuple[str, str]:
    """Identity of a file in results: (platform, source_id), never the basename."""

    return payload.get("platform"), payload.get("source_id")


def group_hits(points) -> "OrderedDict[Tuple[str, str], Dict]":
    """Group Qdrant hits by source: best score, all chunk texts, first payload."""

    groups: "OrderedDict[Tuple[str, str], Dict]" = OrderedDict()

    for point in points:
        payload = point.payload or {}
        key = source_key(payload)
        group = groups.setdefault(key, {"payload": payload, "best": 0.0, "chunks": []})
        group["best"] = max(group["best"], float(point.score))
        if payload.get("chunk"):
            group["chunks"].append(payload["chunk"])

    return groups


def title_name(payload: dict) -> str:
    """Name used for title matching (GitHub: path inside the repo)."""

    if payload.get("platform") == "github":
        return payload.get("source_id", "").split(":", 1)[-1] or payload.get("file", "")

    return payload.get("file", "")


def base_result(payload: dict, result_type: str, score: float) -> dict:

    platform = payload.get("platform")
    source_id = payload.get("source_id")

    result = {
        "type": result_type,
        "file": payload.get("file", ""),
        "path": payload.get("path", ""),
        "platform": platform,
        "source_id": source_id,
        "score": float(score),
        # Kept for older clients: Drive file id / GitHub repo path.
        "file_id": source_id if platform == "google_drive" else (
            source_id.split(":", 1)[-1] if platform == "github" and source_id else None
        ),
    }

    if platform == "github":
        result["owner"] = payload.get("owner")
        result["repo"] = payload.get("repo")
        result["repository_path"] = result["file_id"]

    return result


def dedupe(results: List[dict]) -> List[dict]:
    """One entry per (platform, source_id, type), keeping the best score."""

    best: "OrderedDict[tuple, dict]" = OrderedDict()

    for result in sorted(results, key=lambda r: r["score"], reverse=True):
        key = (result["platform"], result["source_id"], result["type"])
        if key not in best:
            best[key] = result

    return list(best.values())
