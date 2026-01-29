import streamlit as st
import pandas as pd
# import streamlit as st
# import pandas as pd
#
ALL_TEAMS = "All Teams"
ALL_GAMES = "All Games"

# Persisted values (read these everywhere)
K_TEAM = "GLOBAL_TEAM"
K_GAME_ID = "GLOBAL_GAME_ID"
K_GAME_LABEL = "GLOBAL_GAME_LABEL"

# Widget keys (must be same across pages)
W_TEAM = "W_GLOBAL_TEAM"
W_GAME_LABEL = "W_GLOBAL_GAME_LABEL"

def get_global_selection():
    return (
        st.session_state.get(K_TEAM, ALL_TEAMS),
        st.session_state.get(K_GAME_ID, ALL_GAMES),
        st.session_state.get(K_GAME_LABEL, ALL_GAMES),
    )


def _make_game_label(df: pd.DataFrame, game_date_col: str, oteam_col: str) -> pd.Series:
    # Normalize to reduce mismatch
    date = pd.to_datetime(df[game_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    date = date.fillna(df[game_date_col].astype(str)).astype(str).str.strip()
    opp = df[oteam_col].astype(str).str.strip().str.upper()
    return date + " vs " + opp

@st.cache_data
def _load_master(master_csv_path: str, defteam_col: str, game_id_col: str, game_date_col: str, oteam_col: str) -> pd.DataFrame:
    df = pd.read_csv(master_csv_path)

    df["_Team"] = df[defteam_col].astype(str).str.strip() if defteam_col in df.columns else "UNKNOWN"
    df["_GameId"] = df[game_id_col].astype(str).str.strip() if game_id_col in df.columns else "UNKNOWN"

    if game_date_col in df.columns and oteam_col in df.columns:
        df["_GameLabel"] = _make_game_label(df, game_date_col, oteam_col)
    else:
        df["_GameLabel"] = df["_GameId"]

    return df[["_Team", "_GameId", "_GameLabel"]].drop_duplicates()

def ensure_global_team_game_sidebar(
    *,
    master_csv_path: str,
    defteam_col: str,
    game_id_col: str,
    game_date_col: str,
    oteam_col: str,
):
    """
    Global Team/Game sidebar that persists across pages.
    Game selectbox value is GameKey (string), label is display-only.

    Persists into:
      GLOBAL_TEAM, GLOBAL_GAME_ID, GLOBAL_GAME_LABEL

    Widget keys:
      W_GLOBAL_TEAM, W_GLOBAL_GAME_ID
    """
    import streamlit as st
    import pandas as pd

    ALL_TEAMS = "All Teams"
    ALL_GAMES = "All Games"

    K_TEAM = "GLOBAL_TEAM"
    K_GAME_ID = "GLOBAL_GAME_ID"
    K_GAME_LABEL = "GLOBAL_GAME_LABEL"

    W_TEAM = "W_GLOBAL_TEAM"
    W_GAME_ID = "W_GLOBAL_GAME_ID"

    def _make_label(df: pd.DataFrame) -> pd.Series:
        date = pd.to_datetime(df[game_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
        date = date.fillna(df[game_date_col].astype(str)).astype(str).str.strip()
        opp = df[oteam_col].astype(str).str.strip().str.upper()
        return date + " vs " + opp

    @st.cache_data
    def _load_master(path: str) -> pd.DataFrame:
        df = pd.read_csv(path)

        df["_Team"] = df[defteam_col].astype(str).str.strip() if defteam_col in df.columns else "UNKNOWN"
        df["_GameId"] = df[game_id_col].astype(str).str.strip() if game_id_col in df.columns else "UNKNOWN"

        if game_date_col in df.columns and oteam_col in df.columns:
            df["_GameLabel"] = _make_label(df)
        else:
            df["_GameLabel"] = df["_GameId"]

        return df[["_Team", "_GameId", "_GameLabel"]].drop_duplicates()

    master = _load_master(master_csv_path)

    teams = sorted(master["_Team"].dropna().unique().tolist())
    team_options = [ALL_TEAMS] + teams

    # ---- initialize persisted keys as STRINGS ----
    if K_TEAM not in st.session_state:
        st.session_state[K_TEAM] = ALL_TEAMS
    if K_GAME_ID not in st.session_state:
        st.session_state[K_GAME_ID] = ALL_GAMES
    if K_GAME_LABEL not in st.session_state:
        st.session_state[K_GAME_LABEL] = ALL_GAMES

    st.session_state[K_TEAM] = str(st.session_state[K_TEAM])
    st.session_state[K_GAME_ID] = str(st.session_state[K_GAME_ID])
    st.session_state[K_GAME_LABEL] = str(st.session_state[K_GAME_LABEL])

    # ---- initialize widget keys as STRINGS ----
    if W_TEAM not in st.session_state:
        st.session_state[W_TEAM] = st.session_state[K_TEAM]
    if W_GAME_ID not in st.session_state:
        st.session_state[W_GAME_ID] = st.session_state[K_GAME_ID]

    st.session_state[W_TEAM] = str(st.session_state[W_TEAM])
    st.session_state[W_GAME_ID] = str(st.session_state[W_GAME_ID])

    def _games_for_team(team_val: str) -> pd.DataFrame:
        if team_val == ALL_TEAMS:
            sub = master[["_GameId", "_GameLabel"]].drop_duplicates()
            # newest first by label
            sub = sub.sort_values("_GameLabel", ascending=False)
            # optionally include All Games at top
            top = pd.DataFrame({"_GameId": [ALL_GAMES], "_GameLabel": [ALL_GAMES]})
            return pd.concat([top, sub], ignore_index=True)
        sub = master.loc[master["_Team"] == team_val, ["_GameId", "_GameLabel"]].drop_duplicates()
        return sub.sort_values("_GameLabel", ascending=False)

    with st.sidebar:
        st.selectbox("Team", team_options, key=W_TEAM)

        gdf = _games_for_team(str(st.session_state[W_TEAM])).reset_index(drop=True)

        # ensure ids are strings
        gdf["_GameId"] = gdf["_GameId"].astype(str)
        game_ids = gdf["_GameId"].tolist()
        label_by_id = dict(zip(gdf["_GameId"], gdf["_GameLabel"].astype(str)))

        # coerce invalid selection (string-safe)
        cur_id = str(st.session_state[W_GAME_ID])
        if cur_id not in game_ids:
            st.session_state[W_GAME_ID] = (ALL_GAMES if ALL_GAMES in game_ids else (game_ids[0] if game_ids else ALL_GAMES))

        st.selectbox(
            "Game",
            options=game_ids,
            key=W_GAME_ID,
            format_func=lambda gid: label_by_id.get(str(gid), str(gid)),
        )

    chosen_team = str(st.session_state[W_TEAM])
    chosen_game_id = str(st.session_state[W_GAME_ID])
    chosen_game_label = label_by_id.get(chosen_game_id, ALL_GAMES)

    # persist (string-safe)
    st.session_state[K_TEAM] = chosen_team
    st.session_state[K_GAME_ID] = chosen_game_id
    st.session_state[K_GAME_LABEL] = str(chosen_game_label)

    return chosen_team, chosen_game_id, st.session_state[K_GAME_LABEL]



def apply_team_game_filter_to_df(
    df: pd.DataFrame,
    *,
    team_value: str,
    game_id_value: str,
    defteam_col: str,
    game_id_col: str,
):
    df = df.copy()

    if team_value != ALL_TEAMS and defteam_col in df.columns:
        df = df[df[defteam_col].astype(str).str.strip() == str(team_value)]

    if game_id_value != ALL_GAMES and game_id_col in df.columns:
        df = df[df[game_id_col].astype(str).str.strip() == str(game_id_value)]

    return df


def build_app(
    *,
    title: str,
    data_path: str,
    # per-page schema
    defteam_col: str,
    game_id_col: str,
    game_date_col: str,
    oteam_col: str,
    defender_name_cols: list[str],
    outcome_col: str,
    chance_col: str,
    deftype_col: str | None = None,
    navtype_col: str | None = None,
    navtype_label: str = "Screen Nav Type",
    state_prefix: str = "app",
    count_label: str = "picks",
    # master schema (MUST be the same on all pages)
    master_csv_path: str = "picks_defended_test.csv",
    master_defteam_col: str = "DTeamAbbrev",
    master_game_id_col: str = "GameKey",
    master_game_date_col: str = "game_date",
    master_oteam_col: str = "OTeamAbbrev",
):
    st.title(title)

    @st.cache_data
    def load_data(path: str) -> pd.DataFrame:
        return pd.read_csv(path)

    df = load_data(data_path)

    # Build Defender display name
    if len(defender_name_cols) == 2 and all(c in df.columns for c in defender_name_cols):
        df["Defender"] = (
            df[defender_name_cols[0]].astype(str).str.strip()
            + " "
            + df[defender_name_cols[1]].astype(str).str.strip()
        )
    else:
        df["Defender"] = df[defender_name_cols[0]].astype(str).str.strip()

    # (optional) build Game label for display/drilldown
    if game_date_col in df.columns and oteam_col in df.columns:
        df["Game"] = _make_game_label(df, game_date_col, oteam_col)
    else:
        df["Game"] = "UNKNOWN"

    # Normalize key cols
    for c in [defteam_col, game_id_col, outcome_col, chance_col]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # Global sidebar (stable)
    # Read global selection (sidebar must be rendered in the page file)
    team, game_id, game_label = get_global_selection()

    # Apply stable filtering to this df (by GameKey + team)
    df = apply_team_game_filter_to_df(
        df,
        team_value=team,
        game_id_value=game_id,
        defteam_col=defteam_col,
        game_id_col=game_id_col,
    )

    # ---------- the rest of your existing build_app logic ----------
    # IMPORTANT: remove the Team/Game multiselects entirely (keep Defender, DefType, NavType, etc.)

    navtype_col_effective = navtype_col if (navtype_col and navtype_col in df.columns) else None

    def apply_filters(d: pd.DataFrame, filters: dict) -> pd.DataFrame:
        out = d
        for col, selected in filters.items():
            if selected:
                out = out[out[col].isin(selected)]
        return out

    def available_options(d: pd.DataFrame, col: str, filters: dict) -> list:
        other_filters = {k: v for k, v in filters.items() if k != col}
        sub = apply_filters(d, other_filters)
        return (
            sub[col].dropna().astype(str).str.strip().drop_duplicates().sort_values().tolist()
        )

    # global defender filter (shared)
    k_def = "global_sel_defender"
    if k_def not in st.session_state:
        st.session_state[k_def] = []

    # page filters
    k_type = f"{state_prefix}_sel_deftype"
    k_nav  = f"{state_prefix}_sel_navtype"
    if k_type not in st.session_state:
        st.session_state[k_type] = []
    if k_nav not in st.session_state:
        st.session_state[k_nav] = []

    st.sidebar.header("Filters (page)")

    # Def Type (page)
    if deftype_col and deftype_col in df.columns:
        opts = available_options(df, deftype_col, {"Defender": st.session_state[k_def]})
        st.sidebar.multiselect("Def Type", options=opts, key=k_type)

    # Nav Type (page)
    if navtype_col_effective:
        opts = available_options(df, navtype_col_effective, {"Defender": st.session_state[k_def]})
        st.sidebar.multiselect(navtype_label, options=opts, key=k_nav)

    # Defender (global)
    defender_opts = available_options(df, "Defender", {})
    st.sidebar.multiselect("Defender", options=defender_opts, key=k_def)

    filters = {"Defender": st.session_state[k_def]}
    if deftype_col and deftype_col in df.columns:
        filters[deftype_col] = st.session_state[k_type]
    if navtype_col_effective:
        filters[navtype_col_effective] = st.session_state[k_nav]
    f = apply_filters(df, filters)



    st.caption(f"Global selection: Team={team}, Game={game_label}")
    st.caption(f"Rows after filters: **{len(f):,}**")


    # Summary (kept minimal; keep your existing summary formatting if you want)
    st.subheader("Defender Summary")
    grp = f.groupby(["Defender", outcome_col], dropna=False).size().reset_index(name="count")
    piv = grp.pivot(index="Defender", columns=outcome_col, values="count").fillna(0).astype(int)
    piv.insert(0, count_label, piv.sum(axis=1))
    st.dataframe(piv.reset_index(), use_container_width=True, hide_index=True)

    # -----------------------------
    # chance_id table (selected game) + filters (player, outcome, def type)
    # -----------------------------
    if game_id == ALL_GAMES:
        st.info("Select a specific Game (not All Games) to show chance_ids.")
    elif chance_col not in df.columns:
        st.warning(f"'{chance_col}' not found in this CSV.")
    else:
        st.subheader("chance_id list (selected game)")

        # Use df (team+game filtered) as base so the list doesn't disappear due to other page filters.
        # If you want it to respect all page filters, change df -> f below.
        base = df.copy()

        player_col = "Defender" if "Defender" in base.columns else None
        if player_col is None:
            st.warning("No player column found (expected 'Defender').")
            player_options = ["(All)"]
        else:
            player_options = ["(All)"] + sorted(
                base[player_col].dropna().astype(str).str.strip().unique().tolist()
            )

        # Outcome options
        if outcome_col in base.columns:
            outcomes_raw = (
                base[outcome_col].dropna().astype(str).str.strip().unique().tolist()
            )
            lowers = {x.lower() for x in outcomes_raw}
            if {"good", "neutral", "bad"}.issubset(lowers):
                outcome_options = ["(All)", "good", "neutral", "bad"]
            else:
                outcome_options = ["(All)"] + sorted(outcomes_raw)
        else:
            outcome_options = ["(All)"]

        # Def Type options (only if this page has deftype_col)
        deftype_present = bool(deftype_col) and (deftype_col in base.columns)
        if deftype_present:
            deftypes = sorted(base[deftype_col].dropna().astype(str).str.strip().unique().tolist())
            deftype_options = ["(All)"] + deftypes
        else:
            deftype_options = ["(All)"]

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            sel_player = st.selectbox(
                "Player",
                options=player_options,
                key=f"{state_prefix}_ids_player",
            )
        with c2:
            sel_outcome = st.selectbox(
                "Outcome",
                options=outcome_options,
                key=f"{state_prefix}_ids_outcome",
            )
        with c3:
            sel_deftype = st.selectbox(
                "Def Type",
                options=deftype_options,
                key=f"{state_prefix}_ids_deftype",
                disabled=not deftype_present,
            )

        df_ids = base.copy()

        # Apply Player filter
        if sel_player != "(All)" and player_col and player_col in df_ids.columns:
            df_ids = df_ids[df_ids[player_col].astype(str).str.strip() == sel_player]

        # Apply Outcome filter
        if sel_outcome != "(All)" and outcome_col in df_ids.columns:
            if sel_outcome in ["good", "neutral", "bad"]:
                df_ids = df_ids[
                    df_ids[outcome_col].astype(str).str.strip().str.lower() == sel_outcome
                    ]
            else:
                df_ids = df_ids[df_ids[outcome_col].astype(str).str.strip() == sel_outcome]

        # Apply Def Type filter
        if deftype_present and sel_deftype != "(All)":
            df_ids = df_ids[df_ids[deftype_col].astype(str).str.strip() == sel_deftype]

        # Build table
        show_cols = []
        rename_map = {}

        if player_col and player_col in df_ids.columns:
            show_cols.append(player_col)
            rename_map[player_col] = "Player"

        if outcome_col in df_ids.columns:
            show_cols.append(outcome_col)
            rename_map[outcome_col] = "Outcome"

        if deftype_present:
            show_cols.append(deftype_col)
            rename_map[deftype_col] = "Def Type"

        show_cols.append(chance_col)
        rename_map[chance_col] = "chance_id"

        table_df = df_ids[show_cols].copy().rename(columns=rename_map)

        # Clean
        for c in ["Player", "Outcome", "Def Type", "chance_id"]:
            if c in table_df.columns:
                table_df[c] = table_df[c].astype(str).str.strip()

        table_df = table_df.dropna(subset=["chance_id"])
        table_df = table_df[table_df["chance_id"].ne("")]

    st.caption(f"Rows: **{len(table_df):,}**")
    st.caption(f"Unique chance_ids: **{table_df['chance_id'].nunique():,}**")
    st.dataframe(table_df, use_container_width=True, hide_index=True)
