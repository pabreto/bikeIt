import pandas as pd
import gpxpy
import glob
import numpy as np
import osmnx as ox
import os
import ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import textwrap
from datetime import datetime
from PIL import Image
import json
from matplotlib.lines import Line2D
import shutil
import contextily as ctx
from unidecode import unidecode 


def get_graph_stats(graph,district):
    stats_district = district+".json"
    if os.path.exists(stats_district):
        print("Load stats from file ",district)
        with open(stats_district, "r") as f:
            return json.load(f)
    else:
        print("Compute stats")
        G_proj = ox.projection.project_graph(graph)
        nodes_proj = ox.convert.graph_to_gdfs(G_proj, edges=False)
        graph_area_m = nodes_proj.union_all().convex_hull.area
        graph_area_m = nodes_proj.union_all().convex_hull.area
        stats = ox.stats.basic_stats(G_proj, area=graph_area_m, clean_int_tol=15)
        with open(stats_district, "w") as f:
           json.dump(stats, f, indent=2)
    
        return stats

def save_last_read_gps_point(i,district,user):
    os.makedirs("edges/"+user,exist_ok=True)
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
                coords_gpx.append((points.latitude,points.longitude,points.time))
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
                coords_gpx.append((points.latitude,points.longitude))
                dates_gpx.append(points.time.replace(tzinfo=None))
    return coords_gpx, points.time, dates_gpx



def get_list_edges(graph, coords_gpx, dates_gpx, district, user, start=None):
    os.makedirs("edges/"+user,exist_ok=True)
    file_list_edges = "edges/"+user+"/list_edges_"+district+"-"+user+".txt"
    list_edges = []
    
    if start and os.path.isfile(file_list_edges):
        print("starting from file",file_list_edges)
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
                street_name = edge_attributes.get('name')
            else:
                try:
                    street_name = edge_attributes.get('name')[0]
                except:
                    street_name = "Unkwown"
            length_edge = float(edge_attributes.get('length'))
            edge_key = ((u, v, k), street_name, length_edge)

            if edge_key not in {e[:3] for e in list_edges}:
                list_edges.append((*edge_key, edge_date.isoformat()))
                f.write(f"{(*edge_key, edge_date.isoformat())}\n")
    
    save_last_read_gps_point(get_coords_date_gpx(user)[0], district, user)
    return list_edges

def load_last_gps_point(district,user):
    try:
        file_list_edges = "edges/"+user+"/last_gpx_point_"+district+"-"+user+".txt" #bug with reading previous
        with open(file_list_edges, "r") as f:
            return int(f.read())
    except:
        return None
    

def generate_list_edges(graph_dict,user,list_districts):
    list_edges_read={}
    for district in list_districts:
        print("Generating list edges",district, user)
        last_gps_point = load_last_gps_point(district,user)
        coords,_,dates_gpx=get_coords_dates_gpx(user)
        list_edges_read[district] = get_list_edges(graph_dict[district],coords,dates_gpx, district,user,last_gps_point)

    return list_edges_read

def highlight_edges(graph,list_edges,user,color,district,date):
    edge_date_map = {
    data[0]: datetime.fromisoformat(data[3])
    for data in list_edges[user][district]
    }
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


def plot_mapped(graph_dict, user, district, edge_colors, edge_widths, color, date,last_day):
    os.makedirs("plots/"+user, exist_ok=True)
    os.makedirs("stats/"+user, exist_ok=True)
    if user == "Comparison":
        plot_name = f"plots/{user}/{district.replace(' ', '_')}-{user}.png"
        latest_plot = f"plots/{user}/{district.replace(' ', '_')}-{user}.png"
        latest_plot_with_bg = f"plots/{user}/{district.replace(' ', '_')}-bg-{user}.png"

    else:
        plot_name = f"plots/{user}/{district.replace(' ', '_')}-{user}.{date}.png"
        latest_plot = f"plots/{user}/{district.replace(' ', '_')}-{user}.png"
        latest_plot_with_bg = f"plots/{user}/{district.replace(' ', '_')}-bg-{user}.png"

    if user == "Comparison" or ( (user != "Comparison") and (not os.path.isfile(plot_name) ) ):
        print(f"Plotting {district} for {date}")
        
        # 1. Ensure the graph is projected to Web Mercator (EPSG:3857)
        # This is the standard for background tiles
        # G_proj = ox.project_graph(graph_dict, to_crs='EPSG:3857')
        
        # # 2. Get District Boundary and project it to match the graph
        # # Added .iloc[0:1] to ensure we handle the geodataframe correctly
        # boundary_gdf = ox.geocode_to_gdf(district + ", Barcelona, Spain")
        # boundary = boundary_gdf.to_crs(G_proj.crs).iloc[0:1]
        
        # 3. Plot the graph
        fig, ax = ox.plot.plot_graph(
            graph_dict,
            edge_color=edge_colors,
            edge_linewidth=0.5,
            show=False,
            close=False,
            node_size=0,
            bgcolor="white"
        )



        if user == "Comparison":
            legend_elements = [
                Line2D([0], [0], color='red', lw=2, label='Both'),
                Line2D([0], [0], color='blue', lw=2, label='Hubert only'),
                Line2D([0], [0], color='green', lw=2, label='PA only'),
            ]
            ax.legend(handles=legend_elements, loc='lower right')
    
        ax.set_title(f"{district} - {user} ({date})")
        fig.savefig(plot_name, dpi=250, bbox_inches='tight')
        plt.close(fig)
    if (date == last_day):
            try:
                shutil.copy(plot_name,latest_plot)
            except:
                pass 

def get_number_of_mapped_streets(list_edges):
    mapped_street_names = [edge_data[1] for edge_data in list_edges]
    return len(set(mapped_street_names))

def get_number_of_streets(graph):
    
    unique_street_names_from_G = set()

# Iterate over all edges in the graph, retrieving the attribute data for each edge
    for _, _, data in graph.edges(data=True):
        name_entry = normalize_street_name(data.get('name'))
    
    # Check if the 'name' attribute exists
        if name_entry is not None:
            
            if isinstance(name_entry, list):
                # If the value is a list (multiple names), add all individual names to the set
                for name in name_entry:
                    unique_street_names_from_G.add(name)
            elif isinstance(name_entry, str):
            # If the value is a single string, add it to the set
                unique_street_names_from_G.add(name_entry)

# The count of unique street names is the length of the final set
    count_unique_names_G = len(unique_street_names_from_G)
    #print("Total number of streets",count_unique_names_G)
    return count_unique_names_G

def get_final_stats(user, list_edges, graph_dict, list_districts, stats, date):
    stats_file = f"stats/{user}/stats-{user}_{date}.csv"
    try:
        # Find the previous day's file by looking at all CSVs for this user
        all_prev = sorted(glob.glob(f'stats/{user}/stats-{user}_*.csv'))
        # If the current file exists, the 'previous' is the one before it
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
            "number of mapped streets": number_of_mapped_streets,
            "total number of streets": total_number_of_streets,
            "percentage street": np.array(number_of_mapped_streets)/np.array(total_number_of_streets)*100,
            "number of mapped segments ": number_of_mapped_segments,
            "total number of segments" : total_number_of_segments, 
            "percentage segments": np.array(number_of_mapped_segments)/np.array(total_number_of_segments)*100,
            "mapped kms": mapped_kms,
            "total street length": total_street_length,
            "percentage km": np.array(mapped_kms)/np.array(total_street_length)*100
        })
        df.to_csv(stats_file,index=False)
    return df,df_prev
    
def plot_stats(final_table,previous_table,list_districts):
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
        # Header row
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_height(cell.get_height() * 1.8)

        # District names
        if col == 0 and row > 0:
            cell.set_text_props(weight="bold")
            cell.get_text().set_ha("left")

        # Diff columns
        if "diff" in df_display.columns[col] and row > 0:
            cell.set_text_props(color="green", weight="bold")
    plt.tight_layout()
    plt.savefig(filename, dpi=200, bbox_inches="tight")
    plt.close()

def filter_df_for_district(df, list_districts, district_name):
    idx = list_districts.index(district_name)
    return df.iloc[[idx]]

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
    
   # img_objects = [Image.open(f) for f in images]
    
    for img in new_img_objects:
        img.close()

def merge_edges(edge_colors_pa,edge_colors_hubert):
    merged_colors = []
    for i in range(max(len(edge_colors_hubert),len(edge_colors_pa))):
        if edge_colors_hubert[i] == "red" or edge_colors_hubert[i] == "green":
            if edge_colors_pa[i] == "red" or edge_colors_pa[i] == "green":
                merged_colors.append("red") #mapped by both
            else:
                merged_colors.append("blue") #mapped by Hubert only
        else:
            if edge_colors_pa[i] == "red" or edge_colors_pa[i] == "green":
                merged_colors.append("green") #mapped by PA only
            else:
                merged_colors.append("grey") #mapped by hite none
    return merged_colors

def plot_district_user_bars(df, user, district):
    """
    Generates and saves a two-bar vertical chart where colors 'fill' 
    a 100% background bar.
    """
    try:
        # Handle district filtering
        dist_data = filter_df_for_district(df, df['districts'].tolist(), district).iloc[0]
    except (IndexError, KeyError):
        return

    percentage_street = dist_data['percentage street']
    percentage_segments = dist_data['percentage segments']

    labels = ['Streets', 'Segments']
    values = [percentage_street, percentage_segments]
    
    # Determine fill colors
    bar_colors = ['tab:blue', 'tab:red']

    # Create the plot
    fig, ax = plt.subplots(figsize=(3, 7)) 
    
    # Clean up the axis
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.set_ylim(-15, 110) # Room for labels below and title above

    positions = np.arange(len(labels))
    bar_width = 0.6

    # 1. Draw the BACKGROUND bars (the 100% "container")
    ax.bar(positions, [100, 100], width=bar_width, color='#eeeeee', 
           edgecolor='#cccccc', linewidth=0.5)

    # 2. Draw the FILL bars (the actual data)
    bars = ax.bar(positions, values, width=bar_width, color=bar_colors)

    # Add the Title
 #   ax.set_title(f"{district.replace('_', ' ')}\n{user}", fontsize=14, fontweight='bold', pad=25)

    # Add percentage labels below the bars
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, 
                -2, # Just below the baseline
                f"{value:.0f}%", 
                ha='center', va='top', fontsize=12, fontweight='bold')

    # Add category labels (Streets/Segments)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold')
    
    # Optional: Add a "100%" markers or light grid line at the top
    ax.axhline(100, color='white', linewidth=1, linestyle='--', alpha=0.5)

    plt.tight_layout()

    # Save the file
    os.makedirs(os.path.join("stats", user), exist_ok=True)
    clean_dist = district.replace(' ', '_')
    output_filename = os.path.join("stats", user, f"stats_bars_{clean_dist}_{user}.png")
    
    fig.savefig(output_filename, dpi=200)
    plt.close()

from shapely.geometry import Point

def export_snapped_gpx(graph, user, district):
    # Retrieve original coordinates and timestamps
    coords_gpx, _, dates_gpx = get_coords_dates_gpx(user)
    lats = [c[0] for c in coords_gpx]
    lons = [c[1] for c in coords_gpx]

    # Snap all points to find the nearest edges
    edge_ids = ox.nearest_edges(graph, X=lons, Y=lats)
    gdf_edges = ox.graph_to_gdfs(graph, nodes=False)

    # Prepare new GPX structure
    new_gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack(name=f"{user}_{district}_snapped")
    new_gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for i, (u, v, k) in enumerate(edge_ids):
        # 1. Get the actual road geometry (LineString)
        edge_data = gdf_edges.loc[(u, v, k)]
        geometry = edge_data.get('geometry')

        # 2. Identify original point
        original_pt = Point(lons[i], lats[i])

        if geometry is None:
            # Fallback for straight edges without complex geometry
            node_u = graph.nodes[u]
            node_v = graph.nodes[v]
            # Create a simple line between nodes to snap to
            from shapely.geometry import LineString
            geometry = LineString([(node_u['x'], node_u['y']), (node_v['x'], node_v['y'])])

        # 3. Project original point onto the edge to find the closest snapped coordinate
        # .project finds distance along line; .interpolate returns the point at that distance
        snapped_pt = geometry.interpolate(geometry.project(original_pt))

        # 4. Append to GPX (lon, lat)
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(
            latitude=snapped_pt.y,
            longitude=snapped_pt.x,
            time=dates_gpx[i]
        ))

    # Save output
    os.makedirs(f"cleaned_gpx/{user}", exist_ok=True)
    output_path = f"cleaned_gpx/{user}/{district}_snapped.gpx"
    with open(output_path, "w") as f:
        f.write(new_gpx.to_xml())
    
    print(f"Point-snapped GPX saved: {output_path}")

def get_missing_streets(mapped_streets,full_graph):
        # G is your graph
    street_names_full_graph = []

    for u, v, key, data in full_graph.edges(keys=True, data=True):
        name = normalize_street_name(data.get("name"))
        #print(name)
        if name and name != "unkown":
            street_names_full_graph.append(name)

    unique_street_names_full_graph = set()
    for name in street_names_full_graph:
        if isinstance(name, list):
            unique_street_names_full_graph.update(name)
        else:
            unique_street_names_full_graph.add(name)

    return list(unique_street_names_full_graph - mapped_streets)

def normalize_street_name(name):
    if isinstance(name, str):
        return (
            unidecode(name)
            .replace("  ", " ")
            .replace("  "," ")
            .lower()
            .replace("d'", "")
            .replace("l'", "")            
            .replace(" de ", " ")
            .replace(" del ", " ")
            .replace("*","")
        )
    elif isinstance(name, list):
        return [
            unidecode(n)
            .replace("  ", " ")
            .replace(" "," ")
            .lower()
            .replace("d'", "")
            .replace("l'", "")            
            .replace(" de ", " ")
            .replace(" del ", " ")
            .replace("*","")
            for n in name
        ]
