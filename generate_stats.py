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
        default=['Hubert', 'PA'], 
        help="User from which to generate the stats. Default is all (PA, Hubert). Looks for data in segments/user."
    )

parser.add_argument(
        "--districts", 
        nargs='+', 
        default=["Barcelona", "Ciutat_Vella", "Eixample", "Sants_Montjuic", "Les_Corts", "Sarria_Sant_Gervasi", "Gracia", "Horta_Guinardo", "Nou_Barris", "Sant_Andreu", "Sant_Marti"], 
        help="Specific district name or 'all' to process everything."
    )

parser.add_argument(
        "--color", 
        type=str, 
        default="red", 
        help="The highlight color for the mapped streets. Default is 'red'."
    )

parser.add_argument(
        "--generate_missing_streets_user", 
        nargs='+', 
        default=[], 
        help="Generate_missing_streets for which user"
    )
parser.add_argument(
        "--generate_missing_streets_district", 
        nargs='+', 
        default=[], 
        help="Generate_missing_streets for which district"
    )

args = parser.parse_args()

users = args.users
districts = args.districts
color = args.color

if districts == ["all"]:
   list_districts = ["Barcelona", "Ciutat_Vella", "Eixample", "Sants_Montjuic", "Les_Corts", "Sarria_Sant_Gervasi", "Gracia", "Horta_Guinardo", "Nou_Barris", "Sant_Andreu", "Sant_Marti"]
else:
   list_districts = districts    

graph_dict={}
graph_type = "bike" 
os.makedirs("graphs", exist_ok=True)

for district in list_districts:
    filepath = "graphs/"+district+"-"+graph_type+".graphml"
    if not os.path.isfile(filepath):
        graph = ox.convert.to_undirected(ox.graph.graph_from_place(district + " ,Barcelona, Spain", network_type=graph_type))
        ox.save_graphml(G=graph, filepath=filepath)
    else:
        graph = ox.load_graphml(filepath)
    graph_dict[district] = graph

stats={}
for district in list_districts:
    stats[district] = get_graph_stats(graph_dict[district], district)

edge_colors = {user: {} for user in users}
edge_widths = {user: {} for user in users}
street_names_mapped = {user: {} for user in users}
missing_streets = {user: {} for user in users}

for user in users:
    coords, _, dates_gpx = get_coords_dates_gpx(user)
    unique_days = sorted(list(set(d.strftime("%Y-%m-%d") for d in dates_gpx)))
    full_history_edges = generate_list_edges(graph_dict, user, list_districts)
    if args.generate_missing_streets_district :
       for district in args.generate_missing_streets_district:
        if args.generate_missing_streets_user:
            if user in args.generate_missing_streets_user:
                street_names_mapped[district] = { edge[1]for edge in full_history_edges[district] }
                print(f"user-{user},district-{district}")
                missing_streets[district,user] = get_missing_streets(street_names_mapped[district],graph_dict[district])
                print(missing_streets[district,user])
            else:
                continue
    
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
        if user != "Comparison":
            for district in list_districts:
                plot_district_user_bars(
                    final_table,
                    user,
                    district,
                )

for district in list_districts:
    merged_colors = merge_edges(edge_colors["PA"][district], edge_colors["Hubert"][district])
    plot_mapped(
        graph_dict[district],
        "Comparison",
        district,
        merged_colors,
        0.5,
        color,
        current_date,
        last_day
    )


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

    # --- Comparison plot for each district (4 timeseries) ---
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax2 = ax1.twinx()
    
    user_colors = {'PA': 'tab:blue', 'Hubert': 'tab:green'}
    all_lines = []

    for user in users:
        data = full_df[(full_df['districts'] == district) & (full_df['user'] == user)].sort_values('date')
        if data.empty:
            print("empty data",user)
            continue
        
        l_street = ax1.plot(data['date'], data['number of mapped streets'], color=user_colors[user], 
                            linestyle='-', marker='o', label=f'{user} Streets')
        l_segment = ax2.plot(data['date'], data['number of mapped segments'], color=user_colors[user], 
                                linestyle='--', marker='x', label=f'{user} Segments')
        
        all_lines.extend(l_street + l_segment)
        
    ax1.set_xlabel('Date')
    ax1.set_ylabel(f'Number of mapped streets (Total: {total_str})')
    ax2.set_ylabel(f'Number of mapped segments (Total: {total_seg})')
    plt.title(f"{district.replace('_', ' ')} - Comparison")
    
    # Format X-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    
    labs = [l.get_label() for l in all_lines]
    ax1.legend(all_lines, labs, loc='upper left', ncol=2, fontsize='small')
    
    plt.tight_layout()
    os.makedirs(f"plots/Comparison/timeseries/", exist_ok=True)
    plt.savefig(f"plots/Comparison/timeseries/{district}.png")
    plt.close()

# print("Starting GPX geometry export...")
# for user in users:
#         export_snapped_gpx(graph_dict["Barcelona"], user, "Barcelona")