"""Voting fact table (settlement x Knesset election).

Source: the Central Elections Committee per-ballot-box result files, published
on data.gov.il as the ``votes-knesset`` dataset. West Bank settlements appear
as ordinary localities keyed on CBS semel yishuv. We aggregate ballot boxes to
the locality, then derive per-election turnout and a comparable right/religious
bloc vote share.

Requires network egress to data.gov.il; on a restricted sandbox this yields an
empty frame (logged) and the rest of the pipeline proceeds. It populates on the
GitHub Actions runner.
"""
from __future__ import annotations

import io
import json
import re

import pandas as pd

from . import config
from .utils import he_key, http_get, log

# Metadata (non-party) columns in the CEC ballot files, by Hebrew header.
_META_COLS = {
    "שם ישוב", "שם_ישוב", "סמל ישוב", "סמל_ישוב", "קלפי", "ברזל",
    "בזב", "מצביעים", "פסולים", "כשרים", "ריכוז", "שופט", "ת. עדכון",
    "סמל ועדה", "ועדה",
}
# Detect the Knesset number from a resource's name/url/notes. The data.gov.il
# resources are named inconsistently (Hebrew "הכנסת ה-25", English "knesset_25",
# bare filenames like "expb25.csv" or ".../Knesset_25/expb.csv"), so we try
# several signals and validate the number is a plausible Knesset (16-27).
_KNESSET_PATTERNS = [
    re.compile(r"(?:knesset|כנסת)\D{0,8}(\d{2})", re.I),  # word + number
    re.compile(r"\bk[-_ ]?(\d{2})\b", re.I),               # k25 / k-25
    re.compile(r"(?:^|[^0-9])(1[6-9]|2[0-7])(?:[^0-9]|$)"),  # bare 16-27 token
]


def _detect_knesset(res: dict) -> int | None:
    text = " ".join(str(res.get(k, "")) for k in ("name", "url", "notes",
                                                  "description", "id"))
    for pat in _KNESSET_PATTERNS:
        m = pat.search(text)
        if m:
            n = int(m.group(1))
            if 16 <= n <= 27:
                return n
    return None


def _resource_list() -> list[dict]:
    pkg = http_get(f"{config.DATAGOV_BASE}/package_show",
                   cache=config.RAW / "votes_package.json",
                   params={"id": config.DATAGOV_VOTES})
    if not pkg:
        return []
    try:
        return json.loads(pkg)["result"]["resources"]
    except Exception as exc:  # noqa: BLE001
        log(f"WARN bad votes package: {exc}")
        return []


def _has_hebrew_locality_col(df: pd.DataFrame) -> bool:
    return any("שוב" in str(c) and "שם" in str(c) for c in df.columns)


def _read_csv(body: bytes) -> pd.DataFrame | None:
    """Parse a CEC ballot CSV. These are Windows-1255 (Hebrew) with occasional
    ragged rows, so we try several encodings, validate that real Hebrew headers
    came through (guarding against silent mojibake), and fall back to a tolerant
    parse. The specific failures are logged so a bad file is diagnosable."""
    errs: list[str] = []
    fallback = None
    attempts = [
        {"encoding": "cp1255"},
        {"encoding": "iso-8859-8"},
        {"encoding": "utf-8-sig"},
        {"encoding": "cp1255", "encoding_errors": "replace", "on_bad_lines": "skip"},
        {"encoding": "cp1255", "encoding_errors": "replace", "on_bad_lines": "skip",
         "engine": "python", "sep": None},
    ]
    for kw in attempts:
        try:
            df = pd.read_csv(io.BytesIO(body), **kw)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{kw.get('encoding')}:{type(exc).__name__}")
            continue
        if _has_hebrew_locality_col(df):
            return df
        if fallback is None and df.shape[1] > 3:
            fallback = df
    if fallback is not None:
        return fallback
    log(f"    parse attempts failed: {errs}")
    return None


def _aggregate_one(df: pd.DataFrame, knesset: int) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    cols = list(df.columns)
    has = lambda c, *subs: all(s in c for s in subs)  # noqa: E731
    name_col = next((c for c in cols if has(c, "שם", "שוב")), None)
    semel_col = next((c for c in cols if has(c, "סמל", "שוב")), None)
    valid_col = next((c for c in cols if "כשר" in c), None)
    bzb_col = next((c for c in cols if c == "בזב" or has(c, "בעלי", "זכות")), None)
    voters_col = next((c for c in cols if "מצביע" in c), None)
    if not (name_col and valid_col):
        log(f"WARN K{knesset}: missing core columns; headers={cols[:8]}")
        return pd.DataFrame()

    party_cols = [c for c in df.columns if c not in _META_COLS
                  and pd.api.types.is_numeric_dtype(df[c])
                  and c not in (valid_col, bzb_col, voters_col)]
    group_keys = [c for c in (semel_col, name_col) if c]
    agg = {c: "sum" for c in party_cols}
    agg[valid_col] = "sum"
    if bzb_col:
        agg[bzb_col] = "sum"
    if voters_col:
        agg[voters_col] = "sum"
    g = df.groupby(group_keys, dropna=False).agg(agg).reset_index()

    right = [c for c in party_cols if c in config.RIGHT_BLOC_SLATES]
    g["right_bloc_votes"] = g[right].sum(axis=1) if right else 0
    valid = g[valid_col].replace(0, pd.NA)
    g["right_bloc_share"] = (g["right_bloc_votes"] / valid).astype(float)
    # Winning slate per locality.
    g["top_party"] = g[party_cols].idxmax(axis=1)
    g["top_party_share"] = (g[party_cols].max(axis=1) / valid).astype(float)

    out = pd.DataFrame({
        "knesset": knesset,
        "name_he": g[name_col],
        "cbs_semel": pd.to_numeric(g[semel_col], errors="coerce") if semel_col else pd.NA,
        "valid_votes": g[valid_col],
        "eligible": g[bzb_col] if bzb_col else pd.NA,
        "voters": g[voters_col] if voters_col else pd.NA,
        "right_bloc_votes": g["right_bloc_votes"],
        "right_bloc_share": g["right_bloc_share"],
        "top_party": g["top_party"],
        "top_party_share": g["top_party_share"],
    })
    if voters_col and bzb_col:
        out["turnout"] = (g[voters_col] / g[bzb_col].replace(0, pd.NA)).astype(float)
    out["he_join_key"] = out["name_he"].map(he_key)
    return out


def build() -> pd.DataFrame:
    resources = _resource_list()
    log(f"voting: votes-knesset package lists {len(resources)} resources")
    # Pick CSV resources (by declared format OR a .csv url) and tag each with a
    # detected Knesset number. Keep only the latest CSV per Knesset.
    candidates: dict[int, dict] = {}
    for res in resources:
        fmt = str(res.get("format", "")).lower()
        url = str(res.get("url", ""))
        is_csv = fmt == "csv" or url.lower().split("?")[0].endswith(".csv")
        knesset = _detect_knesset(res)
        if not is_csv or knesset is None:
            log(f"  skip resource name={res.get('name','')!r} fmt={fmt!r} "
                f"knesset={knesset}")
            continue
        # Prefer per-ballot-box files (expb) when several CSVs share a Knesset.
        prev = candidates.get(knesset)
        if prev is None or ("expb" in url.lower() and "expb" not in str(prev.get("url", "")).lower()):
            candidates[knesset] = res

    if not candidates:
        log("voting: no usable CSV resources matched (see skip lines above); "
            "empty table")
        return pd.DataFrame(columns=["knesset", "name_he", "cbs_semel",
                                     "valid_votes", "right_bloc_share",
                                     "top_party", "he_join_key"])

    frames = []
    for knesset in sorted(candidates):
        url = candidates[knesset]["url"]
        log(f"  fetching K{knesset}: {url}")
        body = http_get(url, cache=config.RAW / f"votes_k{knesset}.csv", binary=True)
        if not body:
            continue
        df = _read_csv(body)
        if df is None or df.empty:
            log(f"  WARN K{knesset}: could not parse CSV")
            continue
        agg = _aggregate_one(df, knesset)
        if not agg.empty:
            frames.append(agg)
    if not frames:
        log("voting: resources found but none parsed into rows; empty table")
        return pd.DataFrame(columns=["knesset", "name_he", "cbs_semel",
                                     "valid_votes", "right_bloc_share",
                                     "top_party", "he_join_key"])
    out = pd.concat(frames, ignore_index=True)
    log(f"voting: {len(out)} locality-election rows across "
        f"{out['knesset'].nunique()} elections")
    return out


if __name__ == "__main__":
    build().to_csv(config.DB / "voting_raw.csv", index=False)
