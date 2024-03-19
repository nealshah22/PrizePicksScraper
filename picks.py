import datetime
import pandas as pd
from nba import *
import time 

import re

start_time = time.time()

# Function to check if the value is a simple float or not
def is_valid_float(value):
    # This regex matches a string that represents a float number
    return re.fullmatch(r"-?\d+(\.\d+)?", value) is not None

# Read the CSV file again
data = pd.read_csv('LineProps.csv')

# Combine first and last name together with a space
data['Full Name'] = data['Name']

# Organize the information into the specified dictionary structure
prop_dict = {}
stat_abbreviations = {
    "Points": "PTS",
    "Pts+Rebs+Asts": "PRA",
    "Assists": "AST",
    "Rebounds": "TOT_REB",
    "3-PT Made": "FG3",
    "Pts+Rebs": "PR",
    "Pts+Asts": "PA",
    "Blocked Shots": "BLK",
    "Steals": "STL",
    "Rebs+Asts": "RA",
    "Blks+Stls": "BS",
    "Turnovers": "TURNOVERS"
}
for _, row in data.iterrows():
    prop_type = stat_abbreviations.get(row['Prop'], "Unknown")
    full_name = row['Full Name']
    value = row['Value']
    goblin = row['Goblin']
    opponent = row['Opponent']  # Get the Opponent value
    if prop_type not in prop_dict:
        prop_dict[prop_type] = {}
    if full_name not in prop_dict[prop_type]:
        prop_dict[prop_type][full_name] = []
    
    # Append the Opponent as a third value
    prop_dict[prop_type][full_name].append([value, goblin, opponent])

diffs = []

for prop, players in prop_dict.items():
    print(f"Prop: {prop}")
    for player, values in players.items():
        print(prop_dict[prop][player])
        goblin = prop_dict[prop][player][0][1]
        # remove:
        if len(prop_dict[prop][player]) > 1:
            goblin = prop_dict[prop][player][1][1]
        # change:
        if goblin != "Green":
            # print("skipped b/c not green line")
            continue
        # TODO: check if goblin is standard
        # diff = calculatePTSDiff(player, prop_dict[prop][player][0][0], prop)
        value = prop_dict[prop][player][1][0]
        opponent = prop_dict[prop][player][1][2]
            # Check here if the value is a simple float
        if not is_valid_float(str(value)):
            print(f"Skipping player {player} due to invalid value: {value}")
            continue  # Skip this player and move to the next
        
        # print(player)
        zscore = likelihood_metric(player, value, opponent, prop)
        percentage = zscore_to_percentage(zscore)
        if zscore == 404:
            print("Could not find playerID")
            continue
        result = {
            'player': player,
            'prop': prop,
            'value': value,
            # 'avg': diff[1],
            # 'difference': diff[0],
            # 'abs': abs(diff[0]),
            # 'bet': "Under" if diff[0] > 0 else "Over",
            'z score': zscore,
            'zabs': abs(zscore),
            'zbet': "Under" if zscore > 0 else "Over",
            'z percent': percentage
        }
        diffs.append(result)


df = pd.DataFrame(diffs)

df_sorted = df.sort_values(by='zabs', ascending=False)


# Write the DataFrame to an Excel file
current_datetime = datetime.datetime.now()

# Format the date and time as desired
formatted_datetime = current_datetime.strftime("%m-%d_%H-%M")

file_name = "results_" + formatted_datetime + ".xlsx"

# Modify the line to include the formatted date and time
df_sorted.to_excel(file_name, index=False)

end_time = time.time() 
print("Time taken: ", (end_time - start_time)/60, "minutes") 
