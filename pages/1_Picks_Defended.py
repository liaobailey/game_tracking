from utils_defense import build_app, ensure_global_team_game_sidebar
import streamlit as st


ensure_global_team_game_sidebar(
    master_csv_path="picks_defended_test.csv",
    defteam_col="DTeamAbbrev",
    game_id_col="GameKey",
    game_date_col="game_date",
    oteam_col="OTeamAbbrev",
)

build_app(
    title="Picks Defended",
    data_path="picks_defended_test.csv",
    game_id_col="GameKey",
    game_date_col="game_date",
    oteam_col="OTeamAbbrev",
    defteam_col="DTeamAbbrev",
    defender_name_cols=["BallHandlerDefenderName"],
    outcome_col="pick_defense_outcome",
    chance_col="chance_id",
    deftype_col="scr_def_type",
    state_prefix="picks",
    count_label="picks",
)