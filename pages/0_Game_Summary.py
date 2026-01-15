# pages/0_Game_Summary.py
import streamlit as st
import pandas as pd
from pathlib import Path

from utils_defense import (
    ensure_global_team_game_sidebar,
    ALL_TEAMS,
    ALL_GAMES,
)

st.set_page_config(page_title="Game Summary", layout="wide")
st.title("Game Summary")

APP_DIR = Path(__file__).resolve().parents[1]

FILES = {
    "scr":      APP_DIR / "scr_defended_test.csv",
    "iso":      APP_DIR / "iso_defended_test.csv",
    "bhr":      APP_DIR / "picks_defended_test.csv",
    "closeout": APP_DIR / "closeouts_defended_test.csv",
}

# -----------------------------
# GLOBAL (stable) selection from sidebar (shared across pages)
# -----------------------------
team, game_id, game_label = ensure_global_team_game_sidebar(
    master_csv_path="picks_defended_test.csv",
    defteam_col="DTeamAbbrev",
    game_id_col="GameKey",
    game_date_col="game_date",
    oteam_col="OTeamAbbrev",
)

KEY_COLS = ["SeasonKey", "GameKey", "PlayerKey", "firstName", "lastName", "game_date", "OTeamAbbrev", "DTeamAbbrev"]


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # de-dupe columns defensively (prevents "Grouper not 1-dimensional")
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # normalize ids
    for c in ["SeasonKey", "GameKey", "PlayerKey", "DPlayerKey"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # normalize strings
    for c in ["firstName", "lastName", "OTeamAbbrev", "DTeamAbbrev", "game_date"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df


def add_score_cols(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
    x = df[label_col].astype(str).str.strip().str.lower()
    df = df.copy()
    df["good"] = (x == "good").astype("int64")
    df["bad"] = (x == "bad").astype("int64") * -1
    return df


def agg_game_stat(df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    agg = (
        df.groupby(KEY_COLS, dropna=False)
          .agg(**{
              id_col: (id_col, "nunique"),
              "good": ("good", "sum"),
              "bad": ("bad", "sum"),
          })
          .reset_index()
    )
    agg["score"] = agg["good"] + agg["bad"]
    return agg


def cleanup(df: pd.DataFrame, suffix: str, id_col: str) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={
        id_col: f"count_{suffix}",
        "score": f"score_{suffix}",
    })
    # only keep what we need
    keep = KEY_COLS + [f"count_{suffix}", f"score_{suffix}"]
    out = out[keep]
    return out


# -----------------------------
# Load + prep each file
# -----------------------------
scr = load_csv(FILES["scr"])
iso = load_csv(FILES["iso"])
bhr = load_csv(FILES["bhr"])
closeout = load_csv(FILES["closeout"])

# picks file uses DPlayerKey sometimes
if "DPlayerKey" in bhr.columns and "PlayerKey" not in bhr.columns:
    bhr = bhr.rename(columns={"DPlayerKey": "PlayerKey"}).copy()

# scores
scr = add_score_cols(scr, "drive_label")
iso = add_score_cols(iso, "drive_label")
closeout = add_score_cols(closeout, "drive_label")
bhr = add_score_cols(bhr, "pick_defense_outcome")

# aggregates
scr_agg = agg_game_stat(scr, "DriveKey")
iso_agg = agg_game_stat(iso, "DriveKey")
close_agg = agg_game_stat(closeout, "DriveKey")
bhr_agg = agg_game_stat(bhr, "PickKey")

# cleanup (counts + scores only)
scr_c = cleanup(scr_agg, "scr_def", "DriveKey")
iso_c = cleanup(iso_agg, "iso", "DriveKey")
close_c = cleanup(close_agg, "closeout", "DriveKey")
bhr_c = cleanup(bhr_agg, "bhr_def", "PickKey")

# -----------------------------
# Merge
# -----------------------------
result = iso_c.merge(bhr_c, on=KEY_COLS, how="outer")
result = result.merge(scr_c, on=KEY_COLS, how="outer")
result = result.merge(close_c, on=KEY_COLS, how="outer")

# fill numeric nulls
for c in result.columns:
    if c.startswith("count_") or c.startswith("score_"):
        result[c] = pd.to_numeric(result[c], errors="coerce").fillna(0).astype(int)

# totals
result["tot_drives_defended"] = (
    result.get("count_iso", 0)
    + result.get("count_bhr_def", 0)
    + result.get("count_scr_def", 0)
    + result.get("count_closeout", 0)
)

result["tot_drives_score"] = (
    result.get("score_iso", 0)
    + result.get("score_bhr_def", 0)
    + result.get("score_scr_def", 0)
    + result.get("score_closeout", 0)
)

# -----------------------------
# Apply GLOBAL filters
# -----------------------------
f = result.copy()

if team != ALL_TEAMS and "DTeamAbbrev" in f.columns:
    f = f[f["DTeamAbbrev"].astype(str).str.strip() == str(team).strip()]

if game_id != ALL_GAMES:
    f = f[f["GameKey"].astype("Int64") == int(game_id)]

# -----------------------------
# Output table: Defender, Game, totals, counts, scores
# -----------------------------
f["Defender"] = (f["firstName"].astype(str).str.strip() + " " + f["lastName"].astype(str).str.strip()).str.strip()
f["Game"] = f["game_date"].astype(str).str.strip() + " vs " + f["OTeamAbbrev"].astype(str).str.strip()

out = f[[
    "Defender",
    "Game",
    "tot_drives_defended",
    "tot_drives_score",
    "count_bhr_def",
    "count_scr_def",
    "count_iso",
    "count_closeout",
    "score_bhr_def",
    "score_scr_def",
    "score_iso",
    "score_closeout",
]].copy()

out = out.sort_values(["tot_drives_defended", "tot_drives_score"], ascending=[False, False], kind="mergesort")

# global selection caption
sel_bits = []
if team != ALL_TEAMS:
    sel_bits.append(f"Team={team}")
if game_id != ALL_GAMES:
    sel_bits.append(f"Game={game_label}")
if sel_bits:
    st.caption("Global selection: " + ", ".join(sel_bits))

st.dataframe(out, use_container_width=True)
