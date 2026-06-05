import pandas as pd
import glob
# import gpxpy.gpx
# from shapely.geometry import LineString
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# from shapely.geometry import Point
# import contextily as ctx
# import matplotlib.animation as animation
from utils import (get_graph_stats, get_missing_streets,
                   get_coords_dates_gpx, generate_list_edges,
                   plot_mapped, highlight_edges, get_final_stats,
                   dataframe_to_png, filter_df_for_district,
                   plot_stats, create_gif, plot_district_user_bars,
                   merge_edges, plot_user_comparison_table,highlight_edges_passatges)
import osmnx as ox
import os
import re
import argparse
import json
import numpy as np
from collections import defaultdict
matplotlib.use('Agg')
parser = argparse.ArgumentParser()

parser.add_argument(
        "--users",
        nargs='+',
        default=['Hubert', 'PA'],
        help="User from which to generate the stats." +
             "Default is all (PA, Hubert). Looks for data in segments/user."
    )

parser.add_argument(
        "--districts",
        nargs='+',
        default=["Barcelona", "Ciutat_Vella", "Eixample", "Sants_Montjuic",
                 "Les_Corts", "Sarria_Sant_Gervasi", "Gracia",
                 "Horta_Guinardo", "Nou_Barris", "Sant_Andreu", "Sant_Marti"],
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
    list_districts = ["Barcelona", "Ciutat_Vella", "Eixample",
                      "Sants_Montjuic", "Les_Corts",
                      "Sarria_Sant_Gervasi", "Gracia", "Horta_Guinardo",
                      "Nou_Barris", "Sant_Andreu", "Sant_Marti"]
else:
    list_districts = districts

graph_dict = {}
graph_type = "bike"
os.makedirs("graphs", exist_ok=True)

for district in list_districts:
    filepath = "graphs/"+district+"-"+graph_type+".graphml"
    if not os.path.isfile(filepath):
        graph = ox.convert.to_undirected(
            ox.graph.graph_from_place(district + " ,Barcelona, Spain",
                                      network_type=graph_type))
        ox.save_graphml(G=graph, filepath=filepath)
    else:
        graph = ox.load_graphml(filepath)
    edges_to_remove = [
        (u, v, k) for u, v, k, data in graph.edges(keys=True, data=True)
        if data.get('length', 0) < 25
    ]
    graph.remove_edges_from(edges_to_remove)
    graph_dict[district] = graph

stats = {}
for district in list_districts:
    stats[district] = get_graph_stats(graph_dict[district], district)

edge_colors = {user: {} for user in users}
edge_widths = {user: {} for user in users}
edge_passatges_colors = {user: {} for user in users}
edge_passatges_widths = {user: {} for user in users}
street_names_mapped = {user: {} for user in users}
missing_streets = {user: {} for user in users}
all_user_snapshots = {user: {} for user in users}
number_of_mapped_passatges = {user: {d: 0 for d in list_districts} for user in users}
number_of_passatges = {user: {d: 0 for d in list_districts} for user in users}
user_last_days = {}

for user in users:
    coords, _, dates_gpx = get_coords_dates_gpx(user)
    unique_days = sorted(list(set(d.strftime("%Y-%m-%d") for d in dates_gpx)))
    full_history_edges = generate_list_edges(graph_dict, user, list_districts)
    if args.generate_missing_streets_district:
        for district in args.generate_missing_streets_district:
            if args.generate_missing_streets_user:
                if user in args.generate_missing_streets_user:
                    street_names_mapped[district] = {
                        edge[1] for edge in full_history_edges[district]}
                    print(f"user-{user},district-{district}")
                    missing_streets[district, user] = get_missing_streets(
                        street_names_mapped[district],
                        graph_dict[district])
                    print("missing",
                          missing_streets[district, user],
                          len(missing_streets[district, user]))
                else:
                    continue

    last_day = unique_days[-1]
    user_last_days[user] = last_day
    for current_date in unique_days:
        print(f"Processing {user} for {current_date}")
        stats_check_file = f"stats/{user}/stats-{user}.png"

        list_edges_snapshot = {}
        for district in list_districts:
            list_edges_snapshot[district] = [
                e for e in full_history_edges[district]
                if e[3].split('T')[0] <= current_date
            ]
            colors, widths = highlight_edges(
                graph_dict[district], {user: list_edges_snapshot}, user,
                color, district, current_date
                )
            edge_colors[user][district] = colors

            colors_passatges, widths_district = highlight_edges_passatges(
                    graph_dict[district], {user: list_edges_snapshot}, user, color, district, current_date
            )
            edge_passatges_colors[user][district] = colors_passatges
            number_of_mapped_passatges[user][district] = colors_passatges.count("green")+colors_passatges.count("red")
            number_of_passatges[user][district] = colors_passatges.count("black") + colors_passatges.count("green") + colors_passatges.count("red")
            print("user",user,"district",district,"passatges",number_of_mapped_passatges[user][district],"/",number_of_passatges[user][district])
            edge_passatges_widths[user][district] = widths_district

            edge_widths[user][district] = widths
            
        if current_date == last_day:
            all_user_snapshots[user] = {dist: list(edges) for
                                        dist,
                                        edges in list_edges_snapshot.items()}
                                        
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
            plot_mapped(
                graph_dict[district],
                user,
                district,
                edge_passatges_colors[user][district],
                edge_passatges_widths[user][district],
                color,
                current_date,
                last_day,
                passatges=True
                )

        # 📊 Standard Table Generation
        final_table, previous_table = get_final_stats(
                    user, {user: list_edges_snapshot}, graph_dict,
                    list_districts, stats, current_date
        )

        styled_stats = plot_stats(final_table, previous_table, list_districts)
        if current_date == last_day:
            dataframe_to_png(styled_stats.data, stats_check_file,
                             list_districts)
            for district in list_districts:
                table_stats_district = filter_df_for_district(
                    styled_stats.data, list_districts, district)
                dataframe_to_png(
                    table_stats_district,
                    f"stats/{user}/stats-{district}-{user}.png",
                    [district])
                create_gif(district, user)

        # 📊 NEW: Passatges Stats Tracking and Rendering
        passatges_csv = f"stats/{user}/stats-passatges-{user}_{current_date}.csv"
        num_mapped_p = [number_of_mapped_passatges[user][d] for d in list_districts]
        total_p = [number_of_passatges[user][d] for d in list_districts]
        pct_p = [ (m/t)*100 if t > 0 else 0.0 for m, t in zip(num_mapped_p, total_p)]
        
        df_p = pd.DataFrame({
            "districts": list_districts,
            "mapped passatges": num_mapped_p,
            "total passatges": total_p,
            "percentage passatges": pct_p
        })
        os.makedirs(f"stats/{user}", exist_ok=True)
        df_p.to_csv(passatges_csv, index=False)

        if current_date == last_day:
            # Generate primary log table summaries
            dataframe_to_png(df_p, f"stats/{user}/stats-passatges-{user}.png", list_districts)
            for district in list_districts:
                table_p_district = filter_df_for_district(df_p, list_districts, district)
                dataframe_to_png(
                    table_p_district,
                    f"stats/{user}/stats-passatges-{district}-{user}.png",
                    [district]
                )

        if user != "Comparison":
            for district in list_districts:
                plot_district_user_bars(
                    final_table,
                    user,
                    district,
                )

for district in list_districts:
    merged_colors = merge_edges(edge_colors["PA"][district],
                                edge_colors["Hubert"][district])
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
    
    # Also render Comparison View map files for Passatges profiles
    merged_p_colors = merge_edges(edge_passatges_colors["PA"][district],
                                  edge_passatges_colors["Hubert"][district])
    plot_mapped(
        graph_dict[district],
        "Comparison",
        district,
        merged_p_colors,
        0.8,
        color,
        current_date,
        last_day,
        passatges=True
    )

# plot timeseries
path_stats = os.path.join('stats', '*', 'stats-*.csv')
files = [f for f in glob.glob(path_stats) if "passatges" not in f]

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

if data_list:
    full_df = pd.concat(data_list)

    for district in list_districts:
        df_filtered = full_df[full_df['districts'] == district]
        if df_filtered.empty:
            continue
        dist_info = df_filtered.iloc[0]
        total_str = dist_info['total streets']
        total_seg = dist_info['total segments']

        # --- Individual plots for each user (2 timeseries) ---
        for user in users:
            os.makedirs(f"plots/{user}/timeseries/", exist_ok=True)
            data = full_df[(full_df['districts'] == district) &
                           (full_df['user'] == user)].sort_values('date')
            if data.empty:
                continue

            fig, ax1 = plt.subplots(figsize=(10, 6))
            ax2 = ax1.twinx()

            l1 = ax1.plot(data['date'], data['mapped streets'],
                          color='tab:blue', marker='o', label='Streets')
            l2 = ax2.plot(data['date'], data['mapped segments'],
                          color='tab:red', marker='s', label='Segments')

            ax1.set_xlabel('Date')
            ax1.set_ylabel(f'Mapped Street (Total: {total_str})',
                           color='tab:blue')
            ax2.set_ylabel(f'Mapped Segments (Total: {total_seg})',
                           color='tab:red')
            plt.title(f"{district.replace('_', ' ')} - {user}")

            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()

            lns = l1 + l2
            labs = [lab.get_label() for lab in lns]
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
            data = full_df[(full_df['districts'] == district) &
                           (full_df['user'] == user)].sort_values('date')
            if data.empty:
                continue

            l_street = ax1.plot(data['date'], data['mapped streets'],
                                color=user_colors[user],
                                linestyle='-', marker='o',
                                label=f'{user} Streets')
            l_segment = ax2.plot(data['date'], data['mapped segments'],
                                 color=user_colors[user],
                                 linestyle='--', marker='x',
                                 label=f'{user} Segments')

            all_lines.extend(l_street + l_segment)

        ax1.set_xlabel('Date')
        ax1.set_ylabel(f'Mapped streets (Total: {total_str})')
        ax2.set_ylabel(f'Mapped segments (Total: {total_seg})')
        plt.title(f"{district.replace('_', ' ')} - Comparison")

        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        labs = [lAB.get_label() for lAB in all_lines]
        ax1.legend(all_lines, labs, loc='upper left', ncol=2, fontsize='small')

        plt.tight_layout()
        os.makedirs("plots/Comparison/timeseries/", exist_ok=True)
        plt.savefig(f"plots/Comparison/timeseries/{district}.png")
        plt.close()

# Generate the unique dates list
print('Generating unique dates')
base_dir = "plots"
pattern = re.compile(r"(.+)-(.+)\.(\d{4}-\d{2}-\d{2})\.png")
dates = defaultdict(lambda: defaultdict(set))

for user in users:
    user_path = os.path.join(base_dir, user)
    if not os.path.isdir(user_path):
        continue

    for file in os.listdir(user_path):
        match = pattern.match(file)
        if match:
            district, user_name, date = match.groups()
            dates[district][user].add(date)

dates = {
    district: {
        user: sorted(list(date_set))
        for user, date_set in users_dict.items()
    }
    for district, users_dict in dates.items()
}

with open("dates.json", "w") as f:
    json.dump(dates, f, indent=2)

# Create independent containers for the final calculation
pa_data = {"PA": all_user_snapshots["PA"]}
hubert_data = {"Hubert": all_user_snapshots["Hubert"]}
df_pa, _ = get_final_stats("PA", pa_data, graph_dict, list_districts,
                           stats, user_last_days["PA"])
df_h, _ = get_final_stats("Hubert", hubert_data, graph_dict, list_districts,
                          stats, user_last_days["Hubert"])
plot_user_comparison_table(df_pa, df_h, list_districts,
                           "stats/Comparison/stats-Comparison.png")

# Parse latest snapshot passatges logs into Comparison Metrics dataframes
df_pa_p = pd.read_csv(f"stats/PA/stats-passatges-PA_{user_last_days['PA']}.csv")
df_h_p = pd.read_csv(f"stats/Hubert/stats-passatges-Hubert_{user_last_days['Hubert']}.csv")
plot_user_comparison_table(df_pa_p, df_h_p, list_districts,
                           "stats/Comparison/passatges/stats-Comparison.png")

for district in list_districts:
    df_pa_dist = filter_df_for_district(df_pa, list_districts, district)
    df_h_dist = filter_df_for_district(df_h, list_districts, district)
    print(f"Plotting comparison stats for {district}")
    dist_output_path = f"stats/Comparison/stats-{district}-Comparison.png"
    plot_user_comparison_table(df_pa_dist, df_h_dist, [district], dist_output_path)
    
    # Generate District level Comparison Matrix grids for passatges context
    df_pa_p_dist = filter_df_for_district(df_pa_p, list_districts, district)
    df_h_p_dist = filter_df_for_district(df_h_p, list_districts, district)
    dist_p_output_path = f"stats/Comparison/passatges/stat-{district}-Comparison.png"
    plot_user_comparison_table(df_pa_p_dist, df_h_p_dist, [district], dist_p_output_path)