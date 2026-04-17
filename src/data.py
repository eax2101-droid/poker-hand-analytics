import os
import json
import pandas as pd

event_map = {
    0: "check",
    2: "post_big_blind",
    3: "post_small_blind",
    4: "post_big_blind_dead",
    5: "post_small_blind_dead",
    7: "call",
    8: "bet_or_raise",
    9: "deal_board",
    10: "award_pot",
    11: "fold",
    12: "show_hole_cards",
    14: "system_event",
    15: "hand_end_marker",
    16: "return_uncalled_bet",
    18: "system_event_2"
}


def load_json_files(folder_path):
    all_hands = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                if isinstance(data, dict) and "hands" in data:
                    all_hands.extend(data["hands"])
                else:
                    print(f"Skipping file without 'hands': {filename}")

            except json.JSONDecodeError as e:
                print(f"Skipping bad JSON file: {filename}")
                print(f"Line {e.lineno}, column {e.colno}: {e.msg}")

    return all_hands


def build_actions_df(all_hands):
    all_rows = []

    for hand in all_hands:
        seat_to_player = {}

        for player in hand["players"]:
            seat_to_player[player["seat"]] = {
                "player_id": player["id"],
                "player_name": player["name"]
            }

        for event in hand["events"]:
            payload = event["payload"]
            seat = payload.get("seat")

            row = {
                "hand_id": hand["id"],
                "hand_number": int(hand["number"]),
                "timestamp": event["at"],
                "type": payload.get("type"),
                "seat": seat,
                "value": payload.get("value"),
                "action_name": event_map.get(payload.get("type")),
                "player_name": seat_to_player.get(seat, {}).get("player_name"),
                "player_id": seat_to_player.get(seat, {}).get("player_id")
            }

            all_rows.append(row)

    actions_df = pd.DataFrame(all_rows)

    actions_df = actions_df[
        actions_df["action_name"].notna() &
        ~actions_df["action_name"].str.contains("system", na=False)
    ].copy()

    return actions_df

    actions_df = pd.DataFrame(all_rows)

    actions_df = actions_df[
        actions_df["action_name"].notna() &
        ~actions_df["action_name"].str.contains("system", na=False)
    ].copy()

    return actions_df

    actions_df = pd.DataFrame(all_rows)

    actions_df = actions_df[
        actions_df["action_name"].notna() &
        ~actions_df["action_name"].str.contains("system", na=False)
    ].copy()

    return actions_df


def validate_actions_df(df):
    errors = []

    if df["hand_id"].isna().any():
        errors.append("Missing hand_id values")

    if df["timestamp"].isna().any():
        errors.append("Missing timestamps")

    if df["action_name"].isna().any():
        errors.append("Missing action_name values")

    duplicates = df.duplicated(subset=["hand_id", "timestamp", "seat"])
    if duplicates.sum() > 0:
        errors.append(f"{duplicates.sum()} duplicate events found")

    if (df["timestamp"] < 0).any():
        errors.append("Invalid negative timestamps")

    unknown_actions = df[df["action_name"].isna()]["type"].unique()
    if len(unknown_actions) > 0:
        errors.append(f"Unknown action types: {unknown_actions}")

    if errors:
        print("❌ Data validation failed:")
        for e in errors:
            print("-", e)
    else:
        print("✅ Data validation passed")

    return errors



def build_hands_df(all_hands):
    hand_rows = []

    for hand in all_hands:
        hand_rows.append({
            "hand_id": hand.get("id"),
            "hand_number": int(hand.get("number")) if hand.get("number") is not None else None,
            "small_blind": hand.get("smallBlind"),
            "big_blind": hand.get("bigBlind"),
            "dealer_seat": hand.get("dealerSeat"),
            "started_at": hand.get("startedAt"),
            "num_players": len(hand.get("players", []))
        })

    return pd.DataFrame(hand_rows)


def build_players_df(all_hands):
    player_rows = []

    for hand in all_hands:
        for player in hand.get("players", []):
            player_rows.append({
                "player_id": player.get("id"),
                "player_name": player.get("name")
            })

    return pd.DataFrame(player_rows).drop_duplicates()


def build_hand_players_df(all_hands):
    hand_player_rows = []

    for hand in all_hands:
        for player in hand.get("players", []):
            hand_player_rows.append({
                "hand_id": hand.get("id"),
                "hand_number": int(hand.get("number")) if hand.get("number") is not None else None,
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "seat": player.get("seat"),
                "starting_stack": player.get("stack")
            })

    return pd.DataFrame(hand_player_rows)




import re
import os
import json
import pandas as pd

event_map = {
    0: "check",
    2: "post_big_blind",
    3: "post_small_blind",
    4: "post_big_blind_dead",
    5: "post_small_blind_dead",
    7: "call",
    8: "bet_or_raise",
    9: "deal_board",
    10: "award_pot",
    11: "fold",
    12: "show_hole_cards",
    14: "system_event",
    15: "hand_end_marker",
    16: "return_uncalled_bet",
    18: "system_event_2"
}

name_map = {
    "brian": "brian",
    "shiv": "shiv",
    "mak": "mak",
    "ms detainedtsa": "ms",
    "mslaptop": "ms",
    "ms2": "ms",
    "nick c 5 mins": "nick c",
    "revenge bink": "bink",
    "bday bink": "bink",
    "bday dono bink": "bink",
    "bink office": "bink",
    "sf bink": "bink",
    "mike": "bink",
    "bink 69": "bink",
    "jw": "jason",
    "martins brothe": "ms bro",
    "kevlu 30mins": "kevlu",
    "kevy bullet": "kevlu",
    "kevy 15min": "kevy",
    "neechquick": "neech",
    "bink on link": "bink",
    "aud on plane": "aud",
    "fede 20 min": "fede",
    "brian 10 min":"brian",
    "bink late" : "bink",
    "bink in sf" : "bink",
    "mchu 15 min": "mchu"	
}


def clean_name(name):
    if pd.isna(name):
        return name
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def standardize_player_names(df, col="player_name"):
    df = df.copy()
    df[col] = df[col].apply(clean_name)
    df[col] = df[col].replace(name_map)
    return df