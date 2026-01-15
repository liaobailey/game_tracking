import streamlit as st
import pandas as pd

st.set_page_config(page_title="Picks Defended", layout="wide")

DATA_PATH = "picks_defended_test.csv"

# Raw column names from your screenshot
COL_GAME = "Game"
COL_DEFENDER = "BallHandlerDefenderName"
COL_DEFTEAM = "DTeamAbbrev"
COL_DEFTYPE = "scr_def_type"
COL_OUTCOME = "pick_defense_outcome"
COL_CHANCE = "chance_id"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Normalize strings (helps filtering)
    for c in [COL_GAME, COL_DEFENDER, COL_DEFTEAM, COL_DEFTYPE, COL_OUTCOME, COL_CHANCE]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["Game"] = (
            df["game_date"].astype(str).str.strip()
            + " vs "
            + df["OTeamAbbrev"].astype(str).str.strip()
    )

    return df


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df
    for col, selected in filters.items():
        if selected:
            out = out[out[col].isin(selected)]
    return out


def available_options(df: pd.DataFrame, col: str, filters: dict) -> list:
    """
    Options for `col` given all OTHER filters applied.
    """
    other_filters = {k: v for k, v in filters.items() if k != col}
    sub = apply_filters(df, other_filters)
    opts = (
        sub[col]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values(ascending=False if col == COL_GAME else True)
        .tolist()
    )
    return opts


def sanitize_selection(current_sel: list, valid_options: list) -> list:
    """
    Keep only selections that are still valid after cascading updates.
    """
    if not current_sel:
        return []
    valid = set(valid_options)
    return [x for x in current_sel if x in valid]


def make_summary(df: pd.DataFrame) -> pd.DataFrame:
    grp = (
        df.groupby([COL_DEFENDER, COL_OUTCOME], dropna=False)
          .size()
          .reset_index(name="n")
    )

    piv = (
        grp.pivot(index=COL_DEFENDER, columns=COL_OUTCOME, values="n")
           .fillna(0)
           .astype(int)
    )

    # ensure columns exist
    for col in ["good", "neutral", "bad"]:
        if col not in piv.columns:
            piv[col] = 0

    piv = piv[["good", "neutral", "bad"]]
    piv.insert(0, "picks", piv.sum(axis=1))

    # ---- percentage columns ----
    for col in ["good", "neutral", "bad"]:
        piv[f"{col}_pct"] = (piv[col] / piv["picks"]).where(piv["picks"] > 0, 0)

    piv = piv.sort_values(["picks", "good"], ascending=False).reset_index()

    piv = piv.rename(columns={COL_DEFENDER: "defender"})

    return piv


# -----------------------------
# App
# -----------------------------
st.title("Picks Defended Explorer")

df = load_data(DATA_PATH)

# Initialize session state for selections
for key in ["sel_game", "sel_defender", "sel_defteam", "sel_deftype"]:
    if key not in st.session_state:
        st.session_state[key] = []

filters = {
    COL_GAME: st.session_state["sel_game"],
    COL_DEFENDER: st.session_state["sel_defender"],
    COL_DEFTEAM: st.session_state["sel_defteam"],
    COL_DEFTYPE: st.session_state["sel_deftype"],
}

st.sidebar.header("Filters (cascading)")

# Compute options for each filter based on the OTHER filters
game_opts = available_options(df, COL_GAME, filters)
defender_opts = available_options(df, COL_DEFENDER, filters)
defteam_opts = available_options(df, COL_DEFTEAM, filters)
deftype_opts = available_options(df, COL_DEFTYPE, filters)

# Sanitize current selections (drop invalid)
st.session_state["sel_game"] = sanitize_selection(st.session_state["sel_game"], game_opts)
st.session_state["sel_defender"] = sanitize_selection(st.session_state["sel_defender"], defender_opts)
st.session_state["sel_defteam"] = sanitize_selection(st.session_state["sel_defteam"], defteam_opts)
st.session_state["sel_deftype"] = sanitize_selection(st.session_state["sel_deftype"], deftype_opts)

# Render multiselects with updated options
st.session_state["sel_defteam"] = st.sidebar.multiselect(
    "Def Team", options=defteam_opts, default=st.session_state["sel_defteam"]
)
st.session_state["sel_deftype"] = st.sidebar.multiselect(
    "Def Type", options=deftype_opts, default=st.session_state["sel_deftype"]
)
st.session_state["sel_defender"] = st.sidebar.multiselect(
    "Defender", options=defender_opts, default=st.session_state["sel_defender"]
)
st.session_state["sel_game"] = st.sidebar.multiselect(
    "Game (date)", options=game_opts, default=st.session_state["sel_game"]
)

# Apply final filters
filters = {
    COL_GAME: st.session_state["sel_game"],
    COL_DEFENDER: st.session_state["sel_defender"],
    COL_DEFTEAM: st.session_state["sel_defteam"],
    COL_DEFTYPE: st.session_state["sel_deftype"],
}
f = apply_filters(df, filters)

st.caption(f"Rows after filters: **{len(f):,}**")

# Summary
st.subheader("Defender Summary")
summary = make_summary(f)
st.dataframe(
    summary.style.format({
        "good_pct": "{:.1%}",
        "neutral_pct": "{:.1%}",
        "bad_pct": "{:.1%}",
    }),
    use_container_width=True,
    hide_index=True,
)


# Drilldown
st.subheader("Drilldown: Chance IDs")

c1, c2 = st.columns([1, 1])

with c1:
    defender_list = ["(All defenders)"] + summary["defender"].tolist()
    pick_defender = st.selectbox("Defender (optional)", defender_list)

with c2:
    pick_outcome = st.radio("Outcome", ["good", "neutral", "bad"], horizontal=True)

drill = f[f[COL_OUTCOME] == pick_outcome].copy()
if pick_defender != "(All defenders)":
    drill = drill[drill[COL_DEFENDER] == pick_defender]

show_cols = [c for c in [COL_GAME, COL_DEFTEAM, COL_DEFTYPE, COL_DEFENDER, COL_OUTCOME, COL_CHANCE, "PickKey", "GameKey"]
             if c in drill.columns]

drill_view = drill[show_cols].drop_duplicates()
st.write(f"Matching plays: **{len(drill_view):,}**")
st.dataframe(drill_view, use_container_width=True, hide_index=True)

chance_ids = drill_view[COL_CHANCE].dropna().astype(str).unique().tolist()
st.text_area("Chance IDs", value="\n".join(chance_ids), height=180)

# Reset button
if st.sidebar.button("Reset filters"):
    st.session_state["sel_game"] = []
    st.session_state["sel_defender"] = []
    st.session_state["sel_defteam"] = []
    st.session_state["sel_deftype"] = []
    st.rerun()
