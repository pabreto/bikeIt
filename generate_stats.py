import geopandas as gpd
import pandas as pd
import gpxpy
import glob
import gpxpy.gpx
from shapely.geometry import LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from shapely.geometry import Point
import contextily as ctx
import matplotlib.animation as animation
import numpy as np
from utils import *
import osmnx as ox
import os
import ast
import argparse
import re

parser = argparse.ArgumentParser()

parser.add_argument(
        "--users", 
        nargs='+', 
        default=['Béatrice'], 
        help="User from which to generate the stats. Default is all (Béatrice). Looks for data in segments/user."
    )

parser.add_argument(
        "--districts", 
        nargs='+', 
        default=["Limoges", "Centre/Hôtel de Ville/Emailleurs", "Aurence/Corgnac/Cité U/Beaublanc", "Louyat/Vigenal", "La Bastide/La Brégère", "Bénédictins/Montplaisir", "Le Sablard/Limoges Sud", "Puy Las Rodas/Renoir", "Vanteaux/CHU", "Landouge", "Beaubreuil/Limoges Nord", "Beaune les Mines"], 
        help="Specific district name or 'all' to process everything."
    )

parser.add_argument(
        "--color", 
        type=str, 
        default="red", 
        help="The highlight color for the mapped streets. Default is 'red'."
    )

args = parser.parse_args()

users = args.users
districts = args.districts
color = args.color

if districts == ["all"]:
   list_districts = ["Limoges", "Centre/Hôtel de Ville/Emailleurs", "Aurence/Corgnac/Cité U/Beaublanc", "Louyat/Vigenal", "La Bastide/La Brégère", "Bénédictins/Montplaisir", "Le Sablard/Limoges Sud", "Puy Las Rodas/Renoir", "Vanteaux/CHU", "Landouge", "Beaubreuil/Limoges Nord", "Beaune les Mines"]
else:
   list_districts = districts    

graph_dict={}
graph_type = "bike" 
os.makedirs("graphs", exist_ok=True)

for district in list_districts:
    filepath = "graphs/"+district+"-"+graph_type+".graphml"
    if not os.path.isfile(filepath):
        graph = ox.convert.to_undirected(ox.graph.graph_from_place(district + " , Limoges, France", network_type=graph_type))
        ox.save_graphml(G=graph, filepath=filepath)
    else:
        graph = ox.load_graphml(filepath)
    graph_dict[district] = graph

stats={}
for district in list_districts:
    stats[district] = get_graph_stats(graph_dict[district], district)

edge_colors = {user: {} for user in users}
edge_widths = {user: {} for user in users}

for user in users:
    coords, _, dates_gpx = get_coords_dates_gpx(user)
    unique_days = sorted(list(set(d.strftime("%Y-%m-%d") for d in dates_gpx)))
    full_history_edges = generate_list_edges(graph_dict, user, list_districts)
    
    last_day = unique_days[-1]
    for current_date in unique_days:
        print(f"Processing {user} for {current_date}")
        
        list_edges_snapshot = {}
        for district in list_districts:
            list_edges_snapshot[district] = [
                e for e in full_history_edges[district] 
                if e[3].split('T')[0] <= current_date
            ]

            colors, widths = highlight_edges(
                graph_dict[district], {user: list_edges_snapshot}, user, color, district, current_date
            )
            edge_colors[user][district] = colors
            edge_widths[user][district] = widths

        stats_check_file = f"stats/{user}/stats-{user}.png"
        #if not os.path.exists(stats_check_file):
        for district in list_districts:
            plot_mapped(
                graph_dict[district],
                user,
                district,
                edge_colors[user][district],
                edge_widths[user][district],
                color,
                current_date,
                last_day
            )

        
        final_table, previous_table = get_final_stats(
                user, {user: list_edges_snapshot}, graph_dict, list_districts, stats, current_date
        )
        
        styled_stats = plot_stats(final_table, previous_table, list_districts)
        if current_date == last_day:
            dataframe_to_png(styled_stats.data, stats_check_file, list_districts)
            for district in list_districts:
                table_stats_district = filter_df_for_district(styled_stats.data, list_districts, district)
                print("plotting stats",current_date,district,user)
                dataframe_to_png(
                    table_stats_district,
                    f"stats/{user}/stats-{district}-{user}.png",
                    [district]
                )
                create_gif(district, user)



#plot timeseries
path_stats = os.path.join('stats', '*', 'stats-*.csv')
files = glob.glob(path_stats)

data_list = []
for f in files:
    filename = os.path.basename(f)
    match = re.search(r'stats-([^-^_]+)[-_](\d{4}-\d{2}-\d{2})\.csv', filename)
    
    if match:
        user_name, date_str = match.groups()
        df_temp = pd.read_csv(f)
        df_temp.columns = df_temp.columns.str.strip()
        df_temp['user'] = user_name
        df_temp['date'] = pd.to_datetime(date_str)
        data_list.append(df_temp)

full_df = pd.concat(data_list)

for district in list_districts:
    dist_info = full_df[full_df['districts'] == district].iloc[0]
    total_str = dist_info['total number of streets']
    total_seg = dist_info['total number of segments']

    # --- Individual plots for each user (2 timeseries) ---
    for user in users:
        os.makedirs(f"plots/{user}/timeseries/", exist_ok=True)
        data = full_df[(full_df['districts'] == district) & (full_df['user'] == user)].sort_values('date')
        if data.empty:
            continue
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax2 = ax1.twinx()
        
        l1 = ax1.plot(data['date'], data['number of mapped streets'], color='tab:blue', marker='o', label='Streets')
        l2 = ax2.plot(data['date'], data['number of mapped segments'], color='tab:red', marker='s', label='Segments')
        
        ax1.set_xlabel('Date')
        ax1.set_ylabel(f'Mapped Street (Total: {total_str})', color='tab:blue')
        ax2.set_ylabel(f'Mapped Segments (Total: {total_seg})', color='tab:red')
        plt.title(f"{district.replace('_', ' ')} - {user}")
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        
        lns = l1 + l2
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(f"plots/{user}/timeseries/{district}-{user}.png")
        plt.close()
