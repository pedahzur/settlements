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
_KNESSET_RE = re.compile(r"(?:knesset|כנסת)[^0-9]*([12][0-9])", re.I)


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


def _read_csv(body: bytes) -> pd.DataFrame | None:
    for enc in ("utf-8-sig", "cp1255", "utf-8"):
        try:
            return pd.read_csv(io.BytesIO(body), encoding=enc)
        except Exception:  # noqa: BLE001
            continue
    return None


def _aggregate_one(df: pd.DataFrame, knesset: int) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    name_col = next((c for c in df.columns if c in ("שם ישוב", "שם_ישוב")), None)
    semel_col = next((c for c in df.columns if c in ("סמל ישוב", "סמל_ישוב")), None)
    valid_col = next((c for c in df.columns if c == "כשרים"), None)
    bzb_col = next((c for c in df.columns if c == "בזב"), None)
    voters_col = next((c for c in df.columns if c == "מצביעים"), None)
    if not (name_col and valid_col):
        log(f"WARN K{knesset}: missing core columns")
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
    frames = []
    for res in _resource_list():
        fmt = str(res.get("format", "")).lower()
        url = res.get("url", "")
        name = f"{res.get('name','')} {url}"
        if fmt != "csv":
            continue
        m = _KNESSET_RE.search(name)
        if not m:
            continue
        knesset = int(m.group(1))
        if knesset < 19:        # focus on the modern, per-ballot-box era
            continue
        body = http_get(url, cache=config.RAW / f"votes_k{knesset}.csv", binary=True)
        if not body:
            continue
        df = _read_csv(body)
        if df is None or df.empty:
            continue
        frames.append(_aggregate_one(df, knesset))
    if not frames:
        log("voting: no data (likely restricted egress); empty table")
        return pd.DataFrame(columns=["knesset", "name_he", "cbs_semel",
                                     "valid_votes", "right_bloc_share",
                                     "top_party", "he_join_key"])
    res = pd.concat(frames, ignore_index=True)
    log(f"voting: {len(res)} locality-election rows across "
        f"{res['knesset'].nunique()} elections")
    return res


if __name__ == "__main__":
    build().to_csv(config.DB / "voting_raw.csv", index=False)
