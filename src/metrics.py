import duckdb

def compute_pfr(actions_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)

    query = """
    WITH first_flop AS (
        SELECT hand_id, MIN(timestamp) AS flop_time
        FROM actions_df
        WHERE action_name = 'deal_board'
        GROUP BY hand_id
    ),
    preflop_actions AS (
        SELECT a.*
        FROM actions_df a
        LEFT JOIN first_flop f ON a.hand_id = f.hand_id
        WHERE
            a.action_name != 'deal_board'
            AND (f.flop_time IS NULL OR a.timestamp < f.flop_time)
    ),
    per_hand AS (
        SELECT
            hand_id,
            player_name,
            MAX(CASE WHEN action_name = 'bet_or_raise' THEN 1 ELSE 0 END) AS did_raise
        FROM preflop_actions
        WHERE player_name IS NOT NULL
        GROUP BY hand_id, player_name
    )
    SELECT
        player_name,
        SUM(did_raise) * 1.0 / COUNT(*) AS preflop_raise_rate,
        COUNT(*) AS hands_played
    FROM per_hand
    GROUP BY player_name
    HAVING COUNT(*) > 50
    ORDER BY preflop_raise_rate DESC
    """

    return con.execute(query).fetchdf()


def compute_vpip(actions_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)

    query = """
    WITH first_flop AS (
        SELECT hand_id, MIN(timestamp) AS flop_time
        FROM actions_df
        WHERE action_name = 'deal_board'
        GROUP BY hand_id
    ),
    preflop_actions AS (
        SELECT a.*
        FROM actions_df a
        LEFT JOIN first_flop f ON a.hand_id = f.hand_id
        WHERE
            a.action_name != 'deal_board'
            AND (f.flop_time IS NULL OR a.timestamp < f.flop_time)
    ),
    per_hand AS (
        SELECT
            hand_id,
            player_name,
            MAX(
                CASE
                    WHEN action_name IN ('call', 'bet_or_raise') THEN 1
                    ELSE 0
                END
            ) AS voluntarily_put_money_in_pot
        FROM preflop_actions
        WHERE player_name IS NOT NULL
        GROUP BY hand_id, player_name
    )
    SELECT
        player_name,
        SUM(voluntarily_put_money_in_pot) * 1.0 / COUNT(*) AS vpip,
        COUNT(*) AS hands_played
    FROM per_hand
    GROUP BY player_name
    HAVING COUNT(*) > 50
    ORDER BY vpip DESC
    """

    return con.execute(query).fetchdf()


def compute_showdown_win_rate(actions_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)

    query = """
    WITH showdown_appearances AS (
        SELECT DISTINCT hand_id, player_name
        FROM actions_df
        WHERE action_name = 'show_hole_cards'
          AND player_name IS NOT NULL
    ),
    hand_winners AS (
        SELECT DISTINCT hand_id, player_name
        FROM actions_df
        WHERE action_name = 'award_pot'
          AND player_name IS NOT NULL
    )
    SELECT
        s.player_name,
        COUNT(*) AS showdowns_reached,
        COUNT(w.hand_id) AS showdowns_won,
        COUNT(w.hand_id) * 1.0 / COUNT(*) AS showdown_win_rate
    FROM showdown_appearances s
    LEFT JOIN hand_winners w
        ON s.hand_id = w.hand_id
       AND s.player_name = w.player_name
    GROUP BY s.player_name
    HAVING COUNT(*) >= 15
    ORDER BY showdown_win_rate DESC
    """

    return con.execute(query).fetchdf()

def compute_wtsd(actions_df, hand_players_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)
    con.register("hand_players_df", hand_players_df)

    query = """
    -- Hands that reached at least flop
    WITH postflop_hands AS (
        SELECT DISTINCT hand_id
        FROM actions_df
        WHERE action_name = 'deal_board'
    ),

    -- Hands that reached river (3 board deals)
    river_hands AS (
        SELECT hand_id
        FROM actions_df
        WHERE action_name = 'deal_board'
        GROUP BY hand_id
        HAVING COUNT(*) >= 3
    ),

    -- Players who folded in a hand
    player_folds AS (
        SELECT DISTINCT hand_id, player_name
        FROM actions_df
        WHERE action_name = 'fold'
    ),

    -- All player-hand pairs
    player_hands AS (
        SELECT DISTINCT hand_id, player_name
        FROM hand_players_df
    ),

    -- Only hands where player saw flop
    player_postflop_hands AS (
        SELECT p.hand_id, p.player_name
        FROM player_hands p
        JOIN postflop_hands pf
          ON p.hand_id = pf.hand_id
    )

    SELECT
        p.player_name,

        -- numerator: reached river AND didn't fold
        COUNT(DISTINCT CASE
            WHEN r.hand_id IS NOT NULL AND f.hand_id IS NULL
            THEN p.hand_id
        END) AS showdown_hands,

        -- denominator: saw flop
        COUNT(DISTINCT p.hand_id) AS postflop_hands,

        -- WTSD
        COUNT(DISTINCT CASE
            WHEN r.hand_id IS NOT NULL AND f.hand_id IS NULL
            THEN p.hand_id
        END) * 1.0 / COUNT(DISTINCT p.hand_id) AS wtsd_percent

    FROM player_postflop_hands p

    LEFT JOIN river_hands r
        ON p.hand_id = r.hand_id

    LEFT JOIN player_folds f
        ON p.hand_id = f.hand_id
       AND p.player_name = f.player_name

    GROUP BY p.player_name
    HAVING COUNT(DISTINCT p.hand_id) > 50
    ORDER BY wtsd_percent DESC
    """

    return con.execute(query).fetchdf()


def compute_aggression_factor(actions_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)

    query = """
    WITH first_flop AS (
        SELECT hand_id, MIN(timestamp) AS flop_time
        FROM actions_df
        WHERE action_name = 'deal_board'
        GROUP BY hand_id
    ),
    postflop_actions AS (
        SELECT a.*
        FROM actions_df a
        JOIN first_flop f
            ON a.hand_id = f.hand_id
        WHERE a.timestamp > f.flop_time
          AND a.player_name IS NOT NULL
          AND a.action_name IN ('bet_or_raise', 'call')
    )
    SELECT
        player_name,
        SUM(CASE WHEN action_name = 'bet_or_raise' THEN 1 ELSE 0 END) AS raises,
        SUM(CASE WHEN action_name = 'call' THEN 1 ELSE 0 END) AS calls,
        CASE
            WHEN SUM(CASE WHEN action_name = 'call' THEN 1 ELSE 0 END) = 0
            THEN NULL
            ELSE
                SUM(CASE WHEN action_name = 'bet_or_raise' THEN 1 ELSE 0 END) * 1.0
                / SUM(CASE WHEN action_name = 'call' THEN 1 ELSE 0 END)
        END AS aggression_factor,
        COUNT(*) AS total_aggressive_or_call_actions
    FROM postflop_actions
    GROUP BY player_name
    HAVING COUNT(*) > 30
    ORDER BY aggression_factor DESC
    """

    return con.execute(query).fetchdf()


def compute_cbet_rate(actions_df):
    con = duckdb.connect()
    con.register("actions_df", actions_df)

    query = """
    WITH board_cards AS (
        SELECT
            hand_id,
            timestamp,
            ROW_NUMBER() OVER (
                PARTITION BY hand_id
                ORDER BY timestamp
            ) AS board_stage
        FROM actions_df
        WHERE action_name = 'deal_board'
    ),

    flop_window AS (
        SELECT
            f.hand_id,
            f.timestamp AS flop_time,
            t.timestamp AS turn_time
        FROM board_cards f
        LEFT JOIN board_cards t
            ON f.hand_id = t.hand_id
           AND t.board_stage = 2
        WHERE f.board_stage = 1
    ),

    preflop_raises AS (
        SELECT
            a.hand_id,
            a.player_name,
            a.timestamp,
            ROW_NUMBER() OVER (
                PARTITION BY a.hand_id
                ORDER BY a.timestamp DESC
            ) AS rn
        FROM actions_df a
        JOIN flop_window fw
            ON a.hand_id = fw.hand_id
        WHERE a.timestamp < fw.flop_time
          AND a.action_name = 'bet_or_raise'
          AND a.player_name IS NOT NULL
    ),

    last_preflop_raiser AS (
        SELECT hand_id, player_name
        FROM preflop_raises
        WHERE rn = 1
    ),

    flop_bets AS (
        SELECT DISTINCT
            a.hand_id,
            a.player_name
        FROM actions_df a
        JOIN flop_window fw
            ON a.hand_id = fw.hand_id
        WHERE a.timestamp > fw.flop_time
          AND (fw.turn_time IS NULL OR a.timestamp < fw.turn_time)
          AND a.action_name = 'bet_or_raise'
          AND a.player_name IS NOT NULL
    )

    SELECT
        l.player_name,
        COUNT(*) AS opportunities,
        COUNT(f.hand_id) AS cbets,
        COUNT(f.hand_id) * 1.0 / COUNT(*) AS cbet_rate
    FROM last_preflop_raiser l
    LEFT JOIN flop_bets f
        ON l.hand_id = f.hand_id
       AND l.player_name = f.player_name
    GROUP BY l.player_name
    HAVING COUNT(*) > 10
    ORDER BY cbet_rate DESC
    """

    return con.execute(query).fetchdf()


def build_player_summary(actions_df, hand_players_df):
    vpip_df = compute_vpip(actions_df)
    pfr_df = compute_pfr(actions_df)
    aggression_factor_df = compute_aggression_factor(actions_df)
    wtsd_df = compute_wtsd(actions_df, hand_players_df)
    showdown_win_rate_df = compute_showdown_win_rate(actions_df)
    cbet_df = compute_cbet_rate(actions_df)

    final_df = vpip_df.merge(pfr_df, on="player_name", how="outer", suffixes=("_vpip", "_pfr"))
    final_df = final_df.merge(aggression_factor_df, on="player_name", how="outer")
    final_df = final_df.merge(wtsd_df, on="player_name", how="outer", suffixes=("", "_wtsd"))
    final_df = final_df.merge(showdown_win_rate_df, on="player_name", how="outer", suffixes=("", "_showdown"))
    final_df = final_df.merge(cbet_df, on="player_name", how="outer", suffixes=("", "_cbet"))

    if "hands_played_vpip" in final_df.columns:
        final_df = final_df.rename(columns={"hands_played_vpip": "hands_played"})
    if "hands_played_pfr" in final_df.columns:
        final_df = final_df.drop(columns=["hands_played_pfr"])

    columns_to_keep = [
        "player_name",
        "hands_played",
        "vpip",
        "preflop_raise_rate",
        "aggression_factor",
        "wtsd_percent",
        "showdown_win_rate",
        "cbet_rate"
    ]

    existing_columns = [col for col in columns_to_keep if col in final_df.columns]
    final_df = final_df[existing_columns].sort_values("hands_played", ascending=False)

    return final_df
