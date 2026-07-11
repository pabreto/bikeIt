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
        print("Load stats from file ", district)
        with open(stats_district, "r") as f:
            return json.load(f)
    else:
        print("Compute stats")
        G_proj = ox.projection.project_graph(graph)
        nodes_proj = ox.convert.graph_to_gdfs(G_proj, edges=False)
        graph_area_m = nodes_proj.union_all().convex_hull.area
        stats = ox.stats.basic_stats(G_proj, area=graph_area_m, clean_int_tol=15)
        with open(stats_district, "w") as f:
            json.dump(stats, f, indent=2)
        return stats

def save_last_read_gps_point(i, district, user):
    os.makedirs("edges/" + user, exist_ok=True)
    file_list_edges = "edges/" + user + "/last_gpx_point_" + district + "-" + user + ".txt"
    if os.path.isfile(file_list_edges):
        shutil.copy(file_list_edges, file_list_edges + ".prev")
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

def get_coords_dates_gpx(user, start_idx=0):
    """
    Optimized to only extract and return points from start_idx onwards,
    drastically reducing processing time and memory for subsequent runs.
    """
    file = glob.glob(f'segments/{user}/*.gpx')[0] 
    gpx_file = open(file, 'r') 
    gpx = gpxpy.parse(gpx_file) 
    coords_gpx = []
    dates_gpx = []
    
    current_count = 0
    for track in gpx.tracks:
        for s, segment in enumerate(track.segments):
            if (user == 'hubert') & (s in [1, 6]):
                continue
            for points in segment.points:
                # Only keep and process the point if we are past the history threshold
                if current_count >= start_idx:
                    coords_gpx.append((points.latitude, points.longitude))
                    dates_gpx.append(points.time.replace(tzinfo=None))
                current_count += 1
                
    # Return total count of points parsed in this file so we know the next checkpoint index
    return coords_gpx, points.time, dates_gpx, current_count

def get_list_edges(graph, user, district, start=None):
    os.makedirs("edges/" + user, exist_ok=True)
    file_list_edges = "edges/"+user+"/list_edges_"+district+"-"+user+".txt"
    list_edges = []

    if start and os.path.isfile(file_list_edges):
        print(f"starting from file {file_list_edges} (index: {start})")
        with open(file_list_edges, "r") as f:
            for line in f:
                if line.strip():
                    list_edges.append(ast.literal_eval(line))
    else:
        with open(file_list_edges, "w") as f:
            pass 

    idx_start = start if start is not None else 0
    
    # OPTIMIZATION: Only parse the unread fraction of the GPX coordinates
    coords_gpx, _, dates_gpx, total_gpx_points = get_coords_dates_gpx(user, start_idx=idx_start)

    if not coords_gpx:
        return list_edges

    lats = [c[0] for c in coords_gpx]
    lons = [c[1] for c in coords_gpx]
    edges = ox.nearest_edges(graph, X=lons, Y=lats)
    gdf_edges = ox.graph_to_gdfs(graph, nodes=False)

    with open(file_list_edges, "a") as f:
        for (u, v, k), edge_date in zip(edges, dates_gpx):
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

    save_last_read_gps_point(total_gpx_points, district, user)
    return list_edges

def load_last_gps_point(district, user):
    try:
        file_list_edges = "edges/" + user + "/last_gpx_point_" + district + "-" + user + ".txt"
        with open(file_list_edges, "r") as f:
            return int(f.read())
    except Exception:
        return None

def generate_list_edges(graph_dict, user, list_districts):
    list_edges_read = {}
    for district in list_districts:
        print("Generating list edges", district, user)
        last_gps_point = load_last_gps_point(district, user)
        list_edges_read[district] = get_list_edges(graph_dict[district],
                                                   user,
                                                   district,
                                                   last_gps_point)
    return list_edges_read

def highlight_edges(graph, list_edges, user, color, district, date):
    edge_date_map = {
        data[0]: datetime.fromisoformat(data[3]) for
        data in list_edges[user][district]}
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
            edge_colors.append("lightgrey")
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
                edge_widths.append(1)
            else:
                edge_colors.append("black")
                edge_widths.append(1)
        else:
            edge_colors.append("lightgrey")
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
#            edge_linewidth=edge_widths,
            edge_linewidth=0.5,
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
    if (date == last_day):
        try:
            shutil.copy(plot_name, latest_plot)
        except Exception:
            pass

def get_number_of_mapped_streets(list_edges):
    mapped_street_names = [normalize_street_name(edge_data[1]) for
                           edge_data in list_edges]
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
        df.to_csv(stats_file,index=False)
    return df,df_prev

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
                if (diff[col] != 0).any() and col != "total street length":
                    delta_col_name = "diff "+ col
                    new_data[delta_col_name] = diff[col]
                    display_cols.append(delta_col_name)

                df_display = pd.DataFrame(new_data, index=final_table.index)[display_cols]
    else:
        df_display = final_table
    return df_display.style \
        .format(precision=1) \
        .format_index(str.upper, axis=0) \
        .relabel_index(list_districts, axis=0) \
    .apply(lambda x: ['color: green; font-weight: bold' if 'diff' in x.name else '' 
                      for val in x], axis=0)

def wrap_header(text, width=14):
    return "\n".join(textwrap.wrap(text, width=width))

def dataframe_to_png(df, filename, list_districts):
    df_display = df.copy().reset_index(drop=True)
    try:
        df_display.insert(0, "districts", list_districts)
    except:
        pass
    col_labels = [wrap_header(c) for c in df_display.columns]
    cell_text = df_display.round(1).astype(str).values

    n_rows, n_cols = df_display.shape

    fig_width = max(14, n_cols * 1.45)
    fig_height = max(4, n_rows * 0.45)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    col_widths = []
    for col in df_display.columns:
        if col == "districts":
            col_widths.append(0.16)
        elif "diff" in col:
            col_widths.append(0.10)
        else:
            col_widths.append(0.085)
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        cellLoc="center",
        loc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_height(cell.get_height() * 1.8)

        if col == 0 and row > 0:
            cell.set_text_props(weight="bold")
            cell.get_text().set_ha("left")

        cell_text = cell.get_text().get_text()
        if "diff" in df_display.columns[col]:
            try:
                num_val = float(cell_text.replace('%', '').strip())
                if num_val >= 0:
                    cell.set_text_props(color="green", weight="bold")
                else:
                    cell.set_text_props(color="blue", weight="bold")
            except ValueError:
                pass
    plt.tight_layout()
    plt.savefig(filename, dpi=200, bbox_inches="tight")
    plt.close()
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

def filter_df_for_district(df, list_districts, district_name):
    idx = list_districts.index(district_name)
    return df.iloc[[idx]]
    return df[df["districts"] == district_name]

def create_gif(district, user):
    images = sorted(glob.glob("plots/"+user+"/"+district.replace(' ', '_')+"-"+user+".*.png"))
    district_clean = district.replace(" ", "_")
    gif_dir = "gifs/"+user
    gif_name = gif_dir+"/"+district_clean+"-"+user+".gif"
    os.makedirs(gif_dir,exist_ok=True)
    list_processed = f"{gif_dir}/{district_clean}-{user}.json"
    if os.path.exists(list_processed):
        with open(list_processed, "r") as f:
            processed_images = json.load(f)
    else:
        processed_images = []
    new_images = [img for img in images if img not in processed_images]
    new_img_objects = [Image.open(f) for f in new_images]
    if os.path.exists(gif_name):
        existing = Image.open(gif_name)
        existing.save(
                gif_name,
                save_all=True,
                append_images=new_img_objects,
                duration=700,
                loop=1
        )
    else:
        new_img_objects[0].save(
                gif_name,
                save_all=True,
                append_images=new_img_objects[1:],
                duration=700,
                loop=1
        )

    with open(list_processed, "w") as f:
        json.dump(processed_images + new_images, f, indent=2)
    
    if not images: return
    new_img_objects = [Image.open(f) for f in images]
    new_img_objects[0].save(
        gif_name, save_all=True, append_images=new_img_objects[1:], duration=700, loop=1
    )
    for img in new_img_objects:
        img.close()

def merge_edges(edge_colors_pa,edge_colors_hubert):
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
            merged_colors.append(c_h if c_h == "black" else "lightgrey")
    return merged_colors

def plot_district_user_bars(df, user, district, passatges=False):
    """
    Generates and saves a two-bar vertical chart where colors 'fill' 
    a 100% background bar.
    """
    try:
        dist_data = filter_df_for_district(df, df['districts'].tolist(), district).iloc[0]
    except (IndexError, KeyError):
        return

    if passatges:
      percentage_street = dist_data['percentage passatges']
      labels = ['Passatges']
      values = [percentage_street]
      bar_colors = ['tab:blue']

    else:
      percentage_street = dist_data['percentage street']
      percentage_segments = dist_data['percentage segments']
      labels = ['Streets', 'Segments']
      values = [percentage_street, percentage_segments]
      bar_colors = ['tab:blue', 'tab:red']


    fig, ax = plt.subplots(figsize=(3, 7)) 
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.set_ylim(-15, 110)

    positions = np.arange(len(labels))
    bar_width = 0.6

    ax.bar(positions, [100, 100], width=bar_width, color='#eeeeee', 
           edgecolor='#cccccc', linewidth=0.5)

    bars = ax.bar(positions, values, width=bar_width, color=bar_colors)

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, 
                -2, 
                f"{value:.0f}%", 
                ha='center', va='top', fontsize=12, fontweight='bold')

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold')
    ax.axhline(100, color='white', linewidth=1, linestyle='--', alpha=0.5)

    plt.tight_layout()

    os.makedirs(os.path.join("stats", user), exist_ok=True)
    clean_dist = district.replace(' ', '_')
    if passatges:
        output_filename = os.path.join("stats", user, "passatges", f"stats_bars_{clean_dist}_{user}.png")
    #    print("saving for passatges", output_filename)
    else:
        output_filename = os.path.join("stats", user, f"stats_bars_{clean_dist}_{user}.png")
    #    print("saving for streets",output_filename)
    fig.savefig(output_filename, dpi=200)
    plt.close()

def plot_district_user_bars_passatges(df, user, district):
    """
    Generates and saves a single-bar vertical chart for passatges 
    representing the percentage of streets mapped (completely hides segments).
    """
    try:
        # Filter for the specific district row safely
        row = df[df["districts"] == district].iloc[0]
    except (IndexError, KeyError):
        return

    percentage_street = row['percentage passatges']
    labels = ['Passatges']
    values = [percentage_street]
    
    # Render layout setup
    fig, ax = plt.subplots(figsize=(2.5, 7))
    
    # Strip unnecessary borders to maintain design aesthetic
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.set_ylim(-15, 110)
    
    positions = np.arange(len(labels))
    bar_width = 0.5
    
    # 1. Draw the background bar container (representing 100%)
    ax.bar(positions, [100], width=bar_width, color='#E2E8F0', edgecolor='#CBD5E1', linewidth=1.2, zorder=1)
    
    # 2. Draw the active progress fill (using a dark green theme for passatges)
    ax.bar(positions, values, width=bar_width, color='#10B981', zorder=2)
    
    # 3. Annotate text statistics
    # Show active mapped / total value string right above the text percentage label
    mapped_val = int(row['mapped passatges'])
    total_val = int(row['total passatges'])
    
    ax.text(0, values[0] + 2, f"{values[0]:.1f}%", ha='center', va='bottom', fontsize=12, fontweight='bold', color='#065F46', zorder=3)
    ax.text(0, -7, f"{mapped_val}/{total_val}\nMapped", ha='center', va='top', fontsize=10, fontweight='medium', color='#334155', zorder=3)
    
    plt.title(f"{district.replace('_', ' ')}\n({user})", fontsize=11, fontweight='bold', pad=15)
    
    # Ensure save directory scope matches front-end calls
    os.makedirs(f"stats/{user}/passatges", exist_ok=True)
    plt.tight_layout()
    plt.savefig(f"stats/{user}/passatges/bars-{district}-{user}.png", dpi=200)
    plt.close()
def get_missing_streets(mapped_streets, full_graph):
    street_names_full_graph = []

    for u, v, key, data in full_graph.edges(keys=True, data=True):
        name = normalize_street_name(data.get("name"))
        if name:
            street_names_full_graph.append(name)

    unique_street_names_full_graph = set()
    for name in street_names_full_graph:
        if isinstance(name, list):
            unique_street_names_full_graph.add(name[0])
        elif isinstance(name, str):
            unique_street_names_full_graph.add(name)
    print("unique", unique_street_names_full_graph)

    return list(unique_street_names_full_graph - mapped_streets)

def normalize_street_name(name):
    if isinstance(name, str):
        return (
            unidecode(name)
            .replace("  ", " ")
            .replace("  "," ")
            .lower()
            .replace("d'", "")
            .replace("-", " ")
            .replace("l'", "")            
            .replace(" de ", " ")            
            .replace(" del ", " ")
            .replace(" dels ", " ")
            .replace(" el ", " ")
            .replace(" la ", " ")
            .replace(" los ", " ")            
            .replace("les", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace("*","")
        )
    elif isinstance(name, list):
        return [
            unidecode(n)
            .replace("  ", " ")
            .replace(" "," ")
            .lower()
            .replace("d'", "")
            .replace("-", " ")
            .replace("l'", "")            
            .replace(" de ", " ")
            .replace(" del ", " ")
            .replace(" dels ", " ")
            .replace(" el ", " ")
            .replace(" la ", " ")
            .replace(" los ", " ")
            .replace("les", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace("*","")
            for n in name
        ]

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

def plot_short_streets(list_districts):
    print("Plotting short streets for each district...")
    graph_short_streets = {}
    graph_type = "bike"

    for district in list_districts:
        plot_short_streets = f"plots/short_streets-{district}.png"
        if not os.path.isfile(plot_short_streets):
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
                if data.get('length', 0) >= 25
            ]
            graph.remove_edges_from(edges_to_remove)
            graph_short_streets[district] = graph
            fig, ax = ox.plot.plot_graph(
                graph_short_streets[district],
                edge_color="lightgrey",
                edge_linewidth=0.5,
                node_size=0,
                bgcolor="white",
                show=False,
                close=False)
            fig.savefig(plot_short_streets,transparent=True,dpi=250, bbox_inches='tight')
            plt.close(fig) 