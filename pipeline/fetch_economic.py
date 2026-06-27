"""Economic fact table (settlement-level socio-economic standing).

Source: CBS "Characterization and Classification of Local Authorities by the
Socio-Economic Level of the Population" — index value, rank, and cluster
(decile 1-10) per local authority. Settlements that are their own municipality
(Ariel, Ma'ale Adumim, Beitar Illit, Modi'in Illit, Efrat...) match directly;
those inside regional councils inherit at the locality layer where available.

We match on the Hebrew authority name. Network-dependent (CBS); degrades to an
empty table on a restricted sandbox.
"""
from __future__ import annotations

import io

import pandas as pd

from . import config
from .utils import he_key, http_get, log


def _find_columns(df: pd.DataFrame) -> dict | None:
    """Locate the (name, cluster, rank, index) columns by Hebrew keywords."""
    for hdr in range(0, min(12, len(df))):
        row = [str(x) for x in df.iloc[hdr].tolist()]
        joined = " ".join(row)
        if "אשכול" in joined and ("רשות" in joined or "ישוב" in joined or "שם" in joined):
            cols = {}
            for j, cell in enumerate(row):
                c = cell.strip()
                if ("שם" in c and ("רשות" in c or "ישוב" in c)) and "name" not in cols:
                    cols["name"] = j
                elif "אשכול" in c and "cluster" not in cols:
                    cols["cluster"] = j
                elif "דרוג" in c or "דירוג" in c:
                    cols["rank"] = j
                elif "מדד" in c and "ערך" in c:
                    cols["index"] = j
            if "name" in cols and "cluster" in cols:
                cols["_header_row"] = hdr
                return cols
    return None


def build() -> pd.DataFrame:
    body = http_get(config.CBS_SOCIOECONOMIC_XLSX,
                    cache=config.RAW / "cbs_socioeconomic.xlsx", binary=True)
    if not body:
        log("economic: no data (restricted egress); empty table")
        return pd.DataFrame(columns=["name_he", "se_cluster", "se_rank",
                                     "se_index", "he_join_key"])
    try:
        raw = pd.read_excel(io.BytesIO(body), header=None)
    except Exception as exc:  # noqa: BLE001
        log(f"economic: cannot parse CBS xlsx ({exc}); empty table")
        return pd.DataFrame(columns=["name_he", "se_cluster", "se_rank",
                                     "se_index", "he_join_key"])
    cols = _find_columns(raw)
    if not cols:
        log("economic: could not locate header row; empty table")
        return pd.DataFrame(columns=["name_he", "se_cluster", "se_rank",
                                     "se_index", "he_join_key"])
    body_df = raw.iloc[cols["_header_row"] + 1:]
    out = pd.DataFrame({
        "name_he": body_df.iloc[:, cols["name"]].astype(str).str.strip(),
        "se_cluster": pd.to_numeric(body_df.iloc[:, cols["cluster"]], errors="coerce"),
        "se_rank": pd.to_numeric(body_df.iloc[:, cols["rank"]], errors="coerce")
        if "rank" in cols else pd.NA,
        "se_index": pd.to_numeric(body_df.iloc[:, cols["index"]], errors="coerce")
        if "index" in cols else pd.NA,
    })
    out = out[out["name_he"].str.len() > 1].dropna(subset=["se_cluster"])
    out["he_join_key"] = out["name_he"].map(he_key)
    log(f"economic: {len(out)} authorities with socio-economic cluster")
    return out


if __name__ == "__main__":
    build().to_csv(config.DB / "economic.csv", index=False)
