import pandas as pd
import glob
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from utils import (get_graph_stats, get_missing_streets,
                   get_coords_dates_gpx, generate_list_edges,
                   plot_mapped, highlight_edges, get_final_stats,
                   dataframe_to_png, filter_df_for_district,
                   plot_stats, create_gif, plot_district_user_bars,
                   merge_edges, plot_user_comparison_table, highlight_edges_passatges,
                   plot_stats_passatges, plot_district_user_bars_passatges,plot_short_streets)
import osmnx as ox
import os
import re
import argparse
import json
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
plot_short_streets(list_districts)

graph_dict = {}
graph_type = "bike"
os.makedirs("graphs", exist_ok=True)

passatges_cache = {}

for district in list_districts:
    filepath = f"graphs/{district}-{graph_type}.graphml"
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
    # print(f"Removed {len(edges_to_remove)} short edges from {district}")
    graph_dict[district] = graph

    from utils import normalize_street_name
    gdf_edges = ox.graph_to_gdfs(graph, nodes=False)
    passatges_cache[district] = {}
    for edge_id in graph.edges(keys=True):
        edge_attributes = gdf_edges.loc[edge_id]
        name_normalized = normalize_street_name(edge_attributes.get('name'))
        is_p = False
        if isinstance(name_normalized, list):
            is_p = any("passatge" in n for n in name_normalized)
        elif isinstance(name_normalized, str):
            is_p = "passatge" in name_normalized
        passatges_cache[district][edge_id] = is_p

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
user_last_days = {}

passatges_snapshot_logs = {user: defaultdict(list) for user in users}

for user in users:
    coords, _, dates_gpx, _ = get_coords_dates_gpx(user)
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
        stats_passatges_check_file = f"stats/{user}/passatges/stats-{user}.png"

        is_historical_processed = True
        for district in list_districts:
            plot_name = f"plots/{user}/{district.replace(' ', '_')}-{user}.{current_date}.png"
            if current_date != last_day and not os.path.exists(plot_name):
                is_historical_processed = False
                break

        if current_date != last_day and is_historical_processed:
            continue

        print(f"Processing {user} for {current_date}")

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
            edge_widths[user][district] = widths

            colors_passatges, widths_district = highlight_edges_passatges(
                graph_dict[district], {user: list_edges_snapshot}, user, color, 
                district, current_date, passatges_cache[district]
            )
            edge_passatges_colors[user][district] = colors_passatges
            edge_passatges_widths[user][district] = widths_district
            
            mapped_p = colors_passatges.count("green") + colors_passatges.count("red")
            total_p = colors_passatges.count("black") + mapped_p
            passatges_snapshot_logs[user][district].append({
                "date": current_date,
                "mapped passatges": mapped_p,
                "total passatges": total_p
            })

        if current_date == last_day:
            all_user_snapshots[user] = {dist: list(edges) for
                                        dist, edges in list_edges_snapshot.items()}

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
            plot_mapped(graph_dict[district], user, district, edge_passatges_colors[user][district],
                        edge_passatges_widths[user][district], color, current_date, last_day, passatges=True)

        # 📊 Standard Table Generation (Restored to original behavior)
        final_table, previous_table = get_final_stats(
                    user, {user: list_edges_snapshot}, graph_dict,
                    list_districts, stats, current_date
        )

        styled_stats = plot_stats(final_table, previous_table, list_districts)
        
# 📊 Standard Table Generation (Restored to original behavior)
        final_table, previous_table = get_final_stats(
            user, {user: list_edges_snapshot}, graph_dict, list_districts, stats, current_date
        )
        # Ensure raw data columns don't carry unexpected spacing modifications
        final_table.columns = final_table.columns.str.strip()
        if isinstance(previous_table, pd.DataFrame):
            previous_table.columns = previous_table.columns.str.strip()
            
        styled_stats = plot_stats(final_table, previous_table, list_districts)
        
        # 📊 Passatges Table Generation (Keeps custom passatges formatting)
        p_rows = []
        p_prev_rows = []
        p_history_files = sorted(glob.glob(f"stats/{user}/passatges/stats-{user}_*.csv"))
        df_p_prev_disk = pd.read_csv(p_history_files[-2]) if p_history_files else None
        for district in list_districts:
            logs = passatges_snapshot_logs[user][district]
            curr_log = logs[-1]
            p_rows.append({"districts": district, "mapped passatges": curr_log["mapped passatges"], "total passatges": curr_log["total passatges"]})
            
            # If a history file exists on disk, use its data for the previous row; otherwise use current log
            if df_p_prev_disk is not None and district in df_p_prev_disk['districts'].values:
                prev_row_match = df_p_prev_disk[df_p_prev_disk['districts'] == district].iloc[0]
                p_prev_rows.append({"districts": district, "mapped passatges": int(prev_row_match["mapped passatges"]), "total passatges": int(prev_row_match["total passatges"])})
            else:
                p_prev_rows.append({"districts": district, "mapped passatges": curr_log["mapped passatges"], "total passatges": curr_log["total passatges"]})

        df_p_curr = pd.DataFrame(p_rows)
        df_p_curr["percentage passatges"] = (df_p_curr["mapped passatges"] / df_p_curr["total passatges"].replace(0, 1)) * 100
        df_p_prev = pd.DataFrame(p_prev_rows)
        df_p_prev["percentage passatges"] = (df_p_prev["mapped passatges"] / df_p_prev["total passatges"].replace(0, 1)) * 100
        
        styled_p_stats = plot_stats_passatges(df_p_curr, df_p_prev, list_districts)

        if current_date == last_day:
            dataframe_to_png(styled_stats.data, stats_check_file,
                             list_districts)
            os.makedirs(f"stats/{user}/passatges", exist_ok=True)
            dataframe_to_png(styled_p_stats.data, stats_passatges_check_file, list_districts)
            
            for district in list_districts:
                plot_district_user_bars(final_table, user, district, passatges=False) # Unaltered Standard Multi-bar Style
                plot_district_user_bars(df_p_curr, user, district, passatges=True) # Fixed Passatges Single-bar Style
#                plot_district_user_bars(final_table, user, district) # Unaltered Standard Multi-bar Style
#                plot_district_user_bars_passatges(df_p_curr, user, district) # Fixed Passatges Single-bar Style
            for district in list_districts:
                plot_district_user_bars(final_table, user, district, passatges=False) # Original Standard Bar Style
                plot_district_user_bars(df_p_curr, user, district, passatges=True) # New Passatges Bar Style
#                plot_district_user_bars(final_table, user, district) # Original Standard Bar Style
#                plot_district_user_bars_passatges(df_p_curr, user, district) # New Passatges Bar Style
                
                table_stats_district = filter_df_for_district(styled_stats.data, list_districts, district)
                dataframe_to_png(table_stats_district, f"stats/{user}/stats-{district}-{user}.png", [district])
                
                table_p_stats_district = filter_df_for_district(styled_p_stats.data, list_districts, district)
                dataframe_to_png(table_p_stats_district, f"stats/{user}/passatges/stats-{district}-{user}.png", [district])
            #    create_gif(district, user)
            
            df_p_curr.to_csv(f"stats/{user}/passatges/stats-{user}_{last_day}.csv", index=False)

if len(users) >= 2:
    print("Generating Comparative Analytics Datasets...")
    os.makedirs("stats/Comparison/passatges", exist_ok=True)
    os.makedirs("plots/Comparison/timeseries", exist_ok=True)
    
    pa_data = {"PA": all_user_snapshots["PA"]}
    hubert_data = {"Hubert": all_user_snapshots["Hubert"]}
    
    df_pa, _ = get_final_stats("PA", pa_data, graph_dict, list_districts, stats, user_last_days["PA"])
    df_h, _ = get_final_stats("Hubert", hubert_data, graph_dict, list_districts, stats, user_last_days["Hubert"])
    plot_user_comparison_table(df_pa, df_h, list_districts, "stats/Comparison/stats-Comparison.png")

    df_pa_p = pd.read_csv(f"stats/PA/passatges/stats-PA_{user_last_days['PA']}.csv")
    df_h_p = pd.read_csv(f"stats/Hubert/passatges/stats-Hubert_{user_last_days['Hubert']}.csv")
    plot_user_comparison_table(df_pa_p, df_h_p, list_districts, "stats/Comparison/passatges/stats-Comparison.png")

    for district in list_districts:
        df_pa_dist = filter_df_for_district(df_pa, list_districts, district)
        df_h_dist = filter_df_for_district(df_h, list_districts, district)
        plot_user_comparison_table(df_pa_dist, df_h_dist, [district], f"stats/Comparison/stats-{district}-Comparison.png")
        
        df_pa_p_dist = filter_df_for_district(df_pa_p, list_districts, district)
        df_h_p_dist = filter_df_for_district(df_h_p, list_districts, district)
        plot_user_comparison_table(df_pa_p_dist, df_h_p_dist, [district], f"stats/Comparison/passatges/stats-{district}-Comparison.png")

        c_colors = merge_edges(edge_colors["PA"][district], edge_colors["Hubert"][district])
        c_widths = edge_widths["PA"][district]
        plot_mapped(graph_dict[district], "Comparison", district, c_colors, c_widths, color, user_last_days["PA"], user_last_days["PA"], passatges=False)

        c_p_colors = merge_edges(edge_passatges_colors["PA"][district], edge_passatges_colors["Hubert"][district])
        c_p_widths = edge_passatges_widths["PA"][district]
        plot_mapped(graph_dict[district], "Comparison", district, c_p_colors, c_p_widths, color, user_last_days["PA"], user_last_days["PA"], passatges=True)

path_stats = "stats/*/*.csv"
files = glob.glob(path_stats)
files = [f for f in files if "passatges" not in f]
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
        if df_filtered.empty: continue
        
        for user in users:
            os.makedirs(f"plots/{user}/timeseries/", exist_ok=True)
            data = full_df[(full_df['districts'] == district) & (full_df['user'] == user)].sort_values('date')
            if data.empty: continue
            fig, ax1 = plt.subplots(figsize=(10, 6))
            ax2 = ax1.twinx()
            ax1.plot(data['date'], data['mapped streets'], color='tab:blue', marker='o', label='Streets')
            ax2.plot(data['date'], data['mapped segments'], color='tab:red', marker='x', label='Segments')
            plt.title(f"History - {district} ({user})")
            fig.savefig(f"plots/{user}/timeseries/{district}-{user}.png", dpi=200, bbox_inches="tight")
            plt.close(fig)

        if len(users) >= 2:
            data_pa = full_df[(full_df['districts'] == district) & (full_df['user'] == 'PA')].sort_values('date')
            data_hu = full_df[(full_df['districts'] == district) & (full_df['user'] == 'Hubert')].sort_values('date')
            fig, ax = plt.subplots(figsize=(10, 6))
            if not data_pa.empty: ax.plot(data_pa['date'], data_pa['percentage street'], color='forestgreen', marker='o', label='PA %')
            if not data_hu.empty: ax.plot(data_hu['date'], data_hu['percentage street'], color='blue', marker='x', label='Hubert %')
            plt.title(f"Comparison % Streets Mapped - {district}")
            plt.legend()
            fig.savefig(f"plots/Comparison/timeseries/{district}.png", dpi=200, bbox_inches="tight")
            plt.close(fig)
print("All tasks completed successfully!")
