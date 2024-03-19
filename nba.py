from nba_api.stats.endpoints import playercareerstats, cumestatsplayer, teamgamelog, playergamelog, leaguedashptteamdefend, playergamelogs, playerestimatedmetrics
from nba_api.stats.static.players import *
from nba_api.stats.static.teams import *
import pandas as pd
import numpy as np
import json
from scipy.stats import norm
gamesDatabase = {}
statsDatabase = {}
matchupDatabase = {}
player_metrics_cache = None

def zscore_to_percentage(z_score):
    """
    Converts the absolute value of a z-score to a percentage away from 0
    in a normal distribution.

    :param z_score: The z-score (can be negative or positive)
    :return: Percentage of data within the z-score range in a normal distribution.
    """
    abs_z_score = abs(z_score)
    # Using the CDF to find the probability below the z_score
    probability_below_z = norm.cdf(abs_z_score)
    
    # Since the normal distribution is symmetric, the percentage within +/- z_score is:
    percentage_within_z = (probability_below_z - 0.5) * 2 * 100
    
    return percentage_within_z

def calculate_derivative(points):
    if len(points) < 2:
        # If there's only one game (or none), assume no change
        return 0.0
    points.reverse()
    # Calculate the differences between consecutive games
    differences = np.diff(points)
    # Return the average of these differences as the "derivative"
    return np.average(differences)

# finds player id given full name
def getPlayerId(name):
    player = find_players_by_full_name(name)
    if len(player) == 0:
        return 404
    else:
        return player[0]["id"]

# finds the points for the player in the last 5 games
# output may look like: [13.0, 11.0, 9.0, 17.0, 16.0]
def recentPerformance(playerId, prop):
    if playerId == 404:
        return 404
    if playerId in gamesDatabase:
        # print("FOUND PLAYER")
        recentGames = gamesDatabase.get(playerId)
    else:
        # print("DID NOT FIND PLAYER")
        recentGames = recentGameIds(playerId)
        gamesDatabase[playerId] = recentGames
    if recentGames == 404:
        return 404
    record = []
    if playerId not in statsDatabase:
        statsDatabase[playerId] = {}
    for game in recentGames:
        if game in statsDatabase.get(playerId, {}):
            data = statsDatabase[playerId][game]
        else:
            data = cumestatsplayer.CumeStatsPlayer(game_ids=game, league_id='00', player_id=playerId, season='2023-23', season_type_all_star='Regular Season').get_data_frames()[0]
            statsDatabase[playerId][game] = data
        cumStats = json.loads(cumestatsplayer.CumeStatsPlayer(game_ids=game, league_id='00', player_id=playerId, season='2023-23', season_type_all_star='Regular Season').get_json())
        # print(game)
        if prop == "PRA":
            record.append(data['PTS'][0] + data['TOT_REB'][0] + data['AST'][0])
        elif prop == "PR":
            record.append(data['PTS'][0] + data['TOT_REB'][0])
        elif prop == "PA":
            record.append(data['PTS'][0] + data['AST'][0])
        elif prop == "RA":
            record.append(data['TOT_REB'][0] + data['AST'][0])
        elif prop == "BS":
            record.append(data['BLK'][0] + data['STL'][0])
        else:
            record.append(data[prop][0])

    # print('GAME HISTORY')
    # print(record)
    return record

# returns IDs for last 5 games given playerId
def recentGameIds(playerId):
    # gameLog = json.loads(teamgamelog.TeamGameLog(season='2023-24', season_type_all_star='Regular Season', team_id=team).get_json())
    gameLog = json.loads(playergamelog.PlayerGameLog(player_id=playerId, season='2023-24', season_type_all_star='Regular Season').get_json())
    # cumestatsplayer.game_by_game_stats()
    recentGames = []
    for i in range(5):
        try:
            recentGames.append(gameLog['resultSets'][0]['rowSet'][i][2])
        except:
            # If an error occurs, append 0 to recentGames
            return 404
    return recentGames


def playerMatchupHistory(playerId, opponent, prop):
    teaminfo = find_team_by_abbreviation(opponent)
    if prop == "TOT_REB": 
        prop = "REB"
    elif prop == "FG3": 
        prop = "FG3M"
    opponentID = teaminfo.get('id')
    if playerId not in matchupDatabase:
        matchupDatabase[playerId] = {}
    if opponentID in matchupDatabase.get(playerId, {}):
        gameLogs = matchupDatabase[playerId][opponentID]
    else:
        gameLogs = playergamelogs.PlayerGameLogs(player_id_nullable=playerId, opp_team_id_nullable=opponentID, season_nullable='2023-24').get_data_frames()[0]
        matchupDatabase[playerId][opponentID] = gameLogs
    ptsHistory = []
    for _, game in gameLogs.iterrows():
        if prop == "PRA":
            ptsHistory.append(game['PTS'] + game['REB'] + game['AST'])
        elif prop == "PR":
            ptsHistory.append(game['PTS'] + game['REB'])
        elif prop == "PA":
            ptsHistory.append(game['PTS'] + game['AST'])
        elif prop == "RA":
            ptsHistory.append(game['REB'] + game['AST'])
        elif prop == "BS":
            ptsHistory.append(game['BLK'] + game['STL'])
        else:
            ptsHistory.append(game[prop])
        # print(game['MATCHUP'])
    # print("MATCHUP HISTORY")
    # print(ptsHistory)
    return ptsHistory

"""
Calculate a metric indicating the likelihood of a player exceeding a specified number of points in their next game.
Positive values indicate a higher likelihood of exceeding the threshold, while negative values indicate the opposite.

:param player: The full name of the player.
:param value: The threshold of points to determine if the player will exceed or not.
:return: A numerical metric representing the likelihood.
"""

def calculate_trend(data, span=5):
    alpha = 2 / (span + 1)
    ema = [data[0]]  # Initialize EMA with the first data point
    for t in range(1, len(data)):
        ema.append(alpha * data[t] + (1 - alpha) * ema[-1])
    return ema[-1]  # Return the latest EMA value

def likelihood_metric(player, value, opponent, prop):
    playerId = getPlayerId(player)
    points = recentPerformance(playerId, prop)
    if points == 404:
        return 404  # Player not found
    if not points:
        return None  # Insufficient data

    # Trend analysis using EMA
    trend_general = calculate_trend(points)
    
    matchupHistory = playerMatchupHistory(playerId, opponent, prop)
    average_points_specific = np.average(matchupHistory) if matchupHistory else -1
    trend_specific = calculate_trend(matchupHistory) if matchupHistory else trend_general  # Use general trend if no specific history

    # Dynamic weighting
    weight_general = 0.35
    weight_specific = 0.65
    if average_points_specific < 0:
        weight_general = 1.0
        weight_specific = 0.0

    weighted_average_points = (trend_general * weight_general) + (trend_specific * weight_specific)

    std_deviation_general = np.std(points, ddof=1) if np.std(points, ddof=1) != 0 else 1  # Prevent division by zero
    
    # Calculating a score that reflects the over/under estimation
    score = (value - weighted_average_points) / std_deviation_general
    
    # The score is now indicative of over/underestimation and allows for ranking
    return score



# Example usage
# print(calculate_player_score(getPlayerId("Domantas Sabonis"), metrics_weights))

