# Poker Player Style Analysis

This project analyzes poker hand histories to classify player behavior using common poker statistics such as VPIP, PFR, aggression factor, and showdown metrics.

## Overview

Using raw JSON hand history data, this project builds a structured dataset and computes key player-level metrics to understand play styles and tendencies.

## Metrics Implemented

- **VPIP (Voluntarily Put Money in Pot)** — how often a player enters a hand
- **PFR (Preflop Raise Rate)** — how often a player raises preflop
- **Aggression Factor** — ratio of aggressive actions to calls postflop
- **WTSD (Went to Showdown)** — frequency of reaching showdown
- **Showdown Win Rate** — percentage of showdowns won
- **C-Bet Rate** — continuation betting frequency

## Key Visualization

### Player Style Map (VPIP vs PFR)

Players are classified into four archetypes:

- Tight Passive
- Tight Aggressive
- Loose Passive
- Loose Aggressive

This allows quick identification of player tendencies.

## Project Structure
src/
data.py # data loading and cleaning
metrics.py # metric calculations
notebooks/
poker_analysis.ipynb
data/
raw/



## How to Run

1. Install dependencies: pip install -r requirements.txt
   
2. Run the notebook:notebooks/poker_analysis.ipynb

3. 

## Notes

- Player names were standardized to handle inconsistencies across sessions.
- Showdown metrics are approximations based on available action logs.
