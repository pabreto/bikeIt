import pandas as pd
import gpxpy
import glob
import numpy as np
import osmnx as ox
import os
import ast
import matplotlib
import matplotlib.pyplot as plt
import textwrap
from datetime import datetime
from PIL import Image
import json
from matplotlib.lines import Line2D
import shutil
from unidecode import unidecode 
matplotlib.use('Agg')

def get_graph_stats(graph, district):
    stats_district = district+".json"
    if os.path.exists(stats_district):
        with open(stats_district, "r") as f:
            return json.load(f)
    else:
        G_proj = ox.projection.project_graph(graph)
        nodes_proj = ox.convert.graph_to_gdfs(G_proj, edges=False)
        graph_area_m = nodes_proj.union_all().convex_hull.area
        stats = ox.stats.basic_stats(G_proj, area=graph_area_m, clean_int_tol=15)
        with open(stats_district, "w") as f:
            json.dump(stats, f, indent=2)
        return stats

def save_last_read_gps_point(i, district, user):
    os.makedirs("edges/" + user, exist_ok=True)
    file_list_edges = "edges/last_gpx_point_"+district+"-"+user+".txt"
    with open(file_list_edges, "w") as f:
        f.write(str(i))

def get_coords_date_gpx(user):
    file = glob.glob(f'segments/{user}/*.gpx')[0] 
    gpx_file = open(file, 'r') 
    gpx = gpxpy.parse(gpx_file) 
    coords_gpx = []
    for track in gpx.tracks:
        for s, segment in enumerate(track.segments):
            if (user == 'hubert') & (s in [1, 6]):
                continue
            for points in segment.points:
                coords_gpx.append((points.latitude, points.longitude, points.time))
    return coords_gpx, points.time

def get_coords_dates_gpx(user):
    file = glob.glob(f'segments/{user}/*.gpx')[0] 
    gpx_file = open(file, 'r') 
    gpx = gpxpy.parse(gpx_file) 
    coords_gpx = []
    dates_gpx = []
    for track in gpx.tracks:
        for s, segment in enumerate(track.segments):
            if (user == 'hubert') & (s in [1, 6]):
                continue
            for points in segment.points:
                coords_gpx.append((points.latitude, points.longitude))
                dates_gpx.append(points.time.replace(tzinfo=None))
    return coords_gpx, points.time, dates_gpx

def get_list_edges(graph, coords_gpx, dates_gpx, district, user, start=None):
    os.makedirs("edges/" + user, exist_ok=True)
    file_list_edges = "edges/"+user+"/list_edges_"+district+"-"+user+".txt"
    list_edges = []

    if start and os.path.isfile(file_list_edges):
        with open(file_list_edges, "r") as f:
            for line in f:
                if line.strip():
                    list_edges.append(ast.literal_eval(line))
    else:
        with open(file_list_edges, "w") as f:
            pass 

    idx_start = start if start is not None else 0
    to_process = coords_gpx[idx_start:]

    if not to_process:
        return list_edges

    lats = [c[0] for c in to_process]
    lons = [c[1] for c in to_process]
    edges = ox.nearest_edges(graph, X=lons, Y=lats)
    gdf_edges = ox.graph_to_gdfs(graph, nodes=False)

    with open(file_list_edges, "a") as f:
        for (u, v, k), edge_date in zip(edges, dates_gpx[idx_start:]):
            edge_attributes = gdf_edges.loc[(u, v, k)]
            if type(edge_attributes.get('name')) == str:  
                street_name = normalize_street_name(edge_attributes.get('name'))
            else:
                try:
                    street_name = normalize_street_name(edge_attributes.get('name')[0])
                except Exception:
                    street_name = "unkwown"
            length_edge = float(edge_attributes.get('length'))
            edge_key = ((u, v, k), street_name, length_edge)

            if edge_key[0] not in {e[0] for e in list_edges}:
                list_edges.append((*edge_key, edge_date.isoformat()))
                f.write(f"{(*edge_key, edge_date.isoformat())}\n")
    return list_edges

def load_last_gps_point(district, user):
    try:
        file_list_edges = "edges/" + user+"/last_gpx_point_" + district+"-"+user+".txt"
        with open(file_list_edges, "r") as f:
            return int(f.read())
    except Exception:
        return None

def generate_list_edges(graph_dict, user, list_districts):
    list_edges_read = {}
    for district in list_districts:
        last_gps_point = load_last_gps_point(district, user)
        coords, _, dates_gpx = get_coords_dates_gpx(user)
        list_edges_read[district] = get_list_edges(graph_dict[district], coords, dates_gpx, district, user, last_gps_point)
    return list_edges_read

def highlight_edges(graph, list_edges, user, color, district, date):
    edge_date_map = {data[0]: datetime.fromisoformat(data[3]) for data in list_edges[user][district]}
    date_limit = datetime.strptime(date, "%Y-%m-%d")
    edge_colors = []
    edge_widths = []
    for u, v, k in graph.edges(keys=True):
        edge_id = (u, v, k)
        if edge_id in edge_date_map:
            if edge_date_map[edge_id] >= date_limit:
                edge_colors.append("green")
            else:
                edge_colors.append(color)
            edge_widths.append(1)
        else:
            edge_colors.append("grey")
            edge_widths.append(0.5)
    return edge_colors, edge_widths

def highlight_edges_passatges(graph, list_edges, user, color, district, date, structural_cache):
    edge_date_map = {data[0]: datetime.fromisoformat(data[3]) for data in list_edges[user][district]}
    date_limit = datetime.strptime(date, "%Y-%m-%d")
    edge_colors = []
    edge_widths = []

    for u, v, k in graph.edges(keys=True):
        edge_id = (u, v, k)
        is_passatge = structural_cache.get(edge_id, False)

        if is_passatge:
            if edge_id in edge_date_map:
                if edge_date_map[edge_id] >= date_limit:
                    edge_colors.append("green")
                else:
                    edge_colors.append(color)
                edge_widths.append(2)
            else:
                edge_colors.append("black")
                edge_widths.append(1)
        else:
            edge_colors.append("grey")
            edge_widths.append(0.5)
    return edge_colors, edge_widths

def plot_mapped(graph_dict, user, district, edge_colors, edge_widths, color, date, last_day, passatges=False):
    os.makedirs("plots/"+user, exist_ok=True)
    os.makedirs("plots/"+user+"/passatges", exist_ok=True)

    clean_dist = district.replace(' ', '_')
    if user == "Comparison":
        if not passatges:
            plot_name = f"plots/{user}/{clean_dist}-{user}.png"
        else:
            plot_name = f"plots/{user}/passatges/{clean_dist}-{user}.png"
        latest_plot = plot_name
    else:
        if not passatges:
            plot_name = f"plots/{user}/{clean_dist}-{user}.{date}.png"
            latest_plot = f"plots/{user}/{clean_dist}-{user}.png"
        else:
            plot_name = f"plots/{user}/passatges/{clean_dist}-{user}.{date}.png"
            latest_plot = f"plots/{user}/passatges/{clean_dist}-{user}.png"

    if user == "Comparison" or not os.path.isfile(plot_name):
        fig, ax = ox.plot.plot_graph(
            graph_dict,
            edge_color=edge_colors,
            edge_linewidth=edge_widths,
            show=False,
            close=False,
            node_size=0,
            bgcolor="white",
        )

        if user == "Comparison":
            legend_elements = [
                Line2D([0], [0], color='red', lw=2, label='Both'),
                Line2D([0], [0], color='blue', lw=2, label='Hubert only'),
                Line2D([0], [0], color='forestgreen', lw=2, label='PA only'),
            ]
            ax.legend(handles=legend_elements, loc='lower right')

        fig.savefig(plot_name, dpi=250, bbox_inches='tight')
        plt.close(fig)
        
    if date == last_day and user != "Comparison":
        try:
            shutil.copy(plot_name, latest_plot)
        except Exception:
            pass

def get_number_of_mapped_streets(list_edges):
    mapped_street_names = [normalize_street_name(edge_data[1]) for edge_data in list_edges]
    return len(set(mapped_street_names))

def get_number_of_streets(graph):
    unique_street_names_from_G = set()
    for _, _, data in graph.edges(data=True):
        name_entry = normalize_street_name(data.get('name'))
        if name_entry is not None:
            if isinstance(name_entry, list):
                unique_street_names_from_G.add(name_entry[0])
            elif isinstance(name_entry, str):
                unique_street_names_from_G.add(name_entry)
    return len(unique_street_names_from_G)

def get_final_stats(user, list_edges, graph_dict, list_districts, stats, date):
    stats_file = f"stats/{user}/stats-{user}_{date}.csv"
    try:
        all_prev = sorted(glob.glob(f'stats/{user}/stats-{user}_*.csv'))
        if stats_file in all_prev:
            idx = all_prev.index(stats_file)
            prev_stats_file = all_prev[idx-1] if idx > 0 else None
        else:
            prev_stats_file = all_prev[-1] if all_prev else None
        df_prev = pd.read_csv(prev_stats_file) if prev_stats_file else []
    except:
        df_prev = []

    if os.path.exists(stats_file):
        df = pd.read_csv(stats_file)
    else:
        number_of_mapped_streets = []
        total_number_of_streets = []
        number_of_mapped_segments = []
        total_number_of_segments = []
        mapped_kms = []
        total_street_length = []
        for district in list_districts:
            number_of_mapped_streets.append(get_number_of_mapped_streets(list_edges[user][district]))
            total_number_of_streets.append(get_number_of_streets(graph_dict[district]))
            number_of_mapped_segments.append(len(list_edges[user][district]))
            total_number_of_segments.append(stats[district]["m"])
            mapped_kms.append(sum(edge[2] for edge in list_edges[user][district])/1000)
            total_street_length.append(stats[district]["edge_length_total"]/1000)
            
        df = pd.DataFrame({
            "districts": list_districts,
            "mapped streets": number_of_mapped_streets,
            "total streets": total_number_of_streets,
            "percentage street": np.array(number_of_mapped_streets)/np.array(total_number_of_streets)*100,
            "mapped segments": number_of_mapped_segments,
            "total segments" : total_number_of_segments,
            "percentage segments": np.array(number_of_mapped_segments)/np.array(total_number_of_segments)*100,
            "mapped kms": mapped_kms,
            "total street length": total_street_length,
            "percentage km": np.array(mapped_kms)/np.array(total_street_length)*100
        })
        df.to_csv(stats_file, index=False)
    return df, df_prev

# ORIGINAL Standard view styling logic
def plot_stats(final_table, previous_table, list_districts):
    if isinstance(previous_table, pd.DataFrame) and not previous_table.empty:
        diff = final_table.set_index("districts").subtract(previous_table.set_index("districts"), fill_value=0).abs()
        diff = diff.reset_index()
        display_cols = []
        new_data = {}
        for col in final_table.columns:
            if col != "districts":
                new_data[col] = final_table[col]
                display_cols.append(col)
                if col in diff.columns and not col.startswith("total") and "percentage" not in col:
                    new_data[f"new {col}"] = diff[col]
                    display_cols.append(f"new {col}")
        df_display = pd.DataFrame(new_data)
        df_display.insert(0, "districts", final_table["districts"])
    else:
        df_display = final_table.copy()
        for col in final_table.columns:
            if col != "districts" and not col.startswith("total") and "percentage" not in col:
                df_display[f"new {col}"] = 0

    for c in df_display.columns:
        if df_display[c].dtype == float:
            df_display[c] = df_display[c].round(1)

    styled = df_display.style.background_gradient(cmap="Greens", subset=[c for c in df_display.columns if "percentage" in c or "new" in c])
    return styled

# NEW Custom layout styling specifically matching your new requested passatges view
def plot_stats_passatges(final_table, previous_table, list_districts):
    if isinstance(previous_table, pd.DataFrame) and not previous_table.empty:
        diff = final_table.set_index("districts").subtract(previous_table.set_index("districts"), fill_value=0).abs()
        diff = diff.reset_index()
        new_data = {
            "mapped passatges": final_table["mapped passatges"],
            "new passatges": diff["mapped passatges"],
            "total passatges": final_table["total passatges"],
            "percentage passatges": final_table["percentage passatges"]
        }
        df_display = pd.DataFrame(new_data)
        df_display.insert(0, "districts", final_table["districts"])
    else:
        df_display = final_table.copy()
        df_display.insert(2, "new passatges", 0)

    for c in df_display.columns:
        if df_display[c].dtype == float:
            df_display[c] = df_display[c].round(1)

    styled = df_display.style.background_gradient(cmap="Greens", subset=["percentage passatges", "new passatges"])
    return styled

def dataframe_to_png(df, filename, list_districts):
    fig, ax = plt.subplots(figsize=(12, len(list_districts)*0.6 + 1.5))
    ax.axis('tight')
    ax.axis('off')
    
    clean_df = df.copy()
    table = ax.table(cellText=clean_df.values, colLabels=clean_df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.4)
    
    plt.tight_layout()
    fig.savefig(filename, dpi=200, bbox_inches="tight")
    plt.close(fig)

def filter_df_for_district(df, list_districts, district_name):
    if district_name in list_districts:
        idx = list_districts.index(district_name)
        return df.iloc[[idx]]
    return df[df["districts"] == district_name]

def create_gif(district, user):
    images = sorted(glob.glob("plots/"+user+"/"+district.replace(' ', '_')+"-"+user+".*.png"))
    district_clean = district.replace(" ", "_")
    gif_dir = "gifs/"+user
    gif_name = gif_dir+"/"+district_clean+"-"+user+".gif"
    os.makedirs(gif_dir, exist_ok=True)
    
    if not images: return
    new_img_objects = [Image.open(f) for f in images]
    new_img_objects[0].save(
        gif_name, save_all=True, append_images=new_img_objects[1:], duration=700, loop=1
    )
    for img in new_img_objects:
        img.close()

def merge_edges(edge_colors_pa, edge_colors_hubert):
    merged_colors = []
    for i in range(max(len(edge_colors_hubert), len(edge_colors_pa))):
        c_h = edge_colors_hubert[i]
        c_p = edge_colors_pa[i]
        if c_h in ["red", "green"] and c_p in ["red", "green"]:
            merged_colors.append("red")
        elif c_h in ["red", "green"]:
            merged_colors.append("blue")
        elif c_p in ["red", "green"]:
            merged_colors.append("forestgreen")
        else:
            merged_colors.append(c_h if c_h == "black" else "grey")
    return merged_colors

# ORIGINAL unaltered standard bars configuration function
def plot_district_user_bars(df, user, district):
    row = df[df["districts"] == district]
    if row.empty: return
    
    val = row["percentage street"].values[0]
    fig, ax = plt.subplots(figsize=(3, 5))
    ax.bar([user], [val], color="red", width=0.6)
    ax.set_ylim(0, 100)
    ax.grid(axis='y')
    
    clean_dist = district.replace(' ', '_')
    os.makedirs(f"stats/{user}", exist_ok=True)
    output_filename = f"stats/{user}/stats_bars_{clean_dist}_{user}.png"
    fig.savefig(output_filename, dpi=200, bbox_inches="tight")
    plt.close(fig)

# NEW custom configuration function explicitly targeted at passatges indicators
def plot_district_user_bars_passatges(df, user, district):
    row = df[df["districts"] == district]
    if row.empty: return
    
    val = row["percentage passatges"].values[0]
    fig, ax = plt.subplots(figsize=(3, 5))
    ax.bar([user], [val], color="#4A90E2", width=0.6)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percentage (%)")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.title("Passatges %")
    
    clean_dist = district.replace(' ', '_')
    os.makedirs(f"stats/{user}/passatges", exist_ok=True)
    output_filename = f"stats/{user}/passatges/stats_bars_{clean_dist}_{user}.png"
    fig.savefig(output_filename, dpi=200, bbox_inches="tight")
    plt.close(fig)

def plot_user_comparison_table(df_pa, df_hubert, list_districts, filename):
    df_comp = pd.merge(df_pa, df_hubert, on="districts", suffixes=('_PA', '_H'))
    base_cols = [c for c in df_pa.columns if c != "districts" and not c.startswith("total")]
    final_data = {"districts": list_districts}
    
    for col in base_cols:
        col_pa = f"{col}_PA"
        col_h = f"{col}_H"
        final_data[col_pa] = df_comp[col_pa]        
        final_data[col_h] = df_comp[col_h]
        if "percentage" not in col:
            final_data[f"diff {col}"] = (df_comp[col_pa] - df_comp[col_h]).round(1)

    df_final = pd.DataFrame(final_data)
    dataframe_to_png(df_final, filename, list_districts)

def get_missing_streets(mapped_names, graph):
    all_streets = set()
    for _, _, data in graph.edges(data=True):
        n = normalize_street_name(data.get('name'))
        if n:
            if isinstance(n, list): all_streets.add(n[0])
            else: all_streets.add(n)
    return all_streets - mapped_names

def normalize_street_name(name):
    if name is None: return None
    if isinstance(name, str):
        return (unidecode(name).replace("  ", " ").lower().replace("d'", "").replace("-", " ")
                .replace("l'", "").replace(" de ", " ").replace(" del ", " ").replace(" dels ", " ")
                .replace(" el ", " ").replace(" la ", " ").replace(" los ", " ").replace("les", " ")
                .replace("(", " ").replace(")", " ").replace("*", ""))
    elif isinstance(name, list):
        return [normalize_street_name(n) for n in name if n is not None]