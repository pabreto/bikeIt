from nicegui import ui
from utils import plot_track, load_long_lat
import contextily as cx


MAPS_OPTIONS = {
    'Light (grey)': 'CartoDB.Positron',      # Clean, modern, low-contrast for data overlays
    'OpenStreetMap (Standard)': 'OpenStreetMap.Mapnik',           # Default OSM tiles, balanced detail
    'Satellite': 'Esri.WorldImagery',        # High-resolution satellite imagery
    # 'Topographic': 'Stamen.Terrain',             # Topographic map with shaded relief
    # 'High Contrast B&W': 'Stamen.Toner',           # Black-and-white map good for printing
    'Dark Mode': 'CartoDB.DarkMatter',      # Dark-themed base map for night or contrast
    # '(Elevation Focused': 'OpenTopoMap',             # Open-source terrain and elevation map
    'Detailed Streets': 'Esri.WorldStreetMap'  # Detailed street-level map
}
COLORS = ['blue', 'black', 'white', 'darkblue', 'red', 'tomato', 'forestgreen']


def get_map_style_object(map_path: str):
    """
    """
    base = cx.providers

    # Split the path by dots (e.g., ['CartoDB', 'Positron'])
    parts = map_path.split('.')

    # Recursively use getattr to navigate the structure
    map_object = base
    for part in parts:
        try:
            map_object = getattr(map_object, part)
        except AttributeError:
            raise ValueError(f"map not found: {map_path}",
                             f"(part: {part}). Check contextily version.")

    # This returns the actual map object reference
    return map_object


selected_names = []
gpx_infos = {}
colors = {'hubert': 'cornflowerblue',
          'pa': 'tomato'}
lws = {'hubert': 7,
       'pa': 7}
initial_selection_key = list(MAPS_OPTIONS.keys())[0]
selected_map_path = MAPS_OPTIONS[initial_selection_key]
current_map_object = get_map_style_object(selected_map_path)


def handle_map_change(event):
    global selected_maps_path, current_map_object
    selected_display_name = event.value
    selected_map_path = MAPS_OPTIONS[selected_display_name]
    current_map_object = get_map_style_object(selected_map_path)
    display_map.refresh()


def handle_hubert_color_change(event):
    colors['hubert'] = event.value
    display_map.refresh()


def handle_pa_color_change(event):
    colors['pa'] = event.value
    display_map.refresh()


def handle_hubert_lw_change(event):
    lws['hubert'] = event.value


def update_selection(name: str, is_checked: bool):
    """
    Updates the selected_names list based on the checkbox state.
    """
    if is_checked and name not in selected_names:
        selected_names.append(name)
        for name in selected_names:
            if name not in gpx_infos.keys():
                gpx_infos[name] = {}
                track, longs_tot, lats_tot = load_long_lat(name,
                                                           n_segments=None)
                gpx_infos[name]['longs'] = longs_tot
                gpx_infos[name]['lats'] = lats_tot
                gpx_infos[name]['track'] = track
        display_map.refresh()

    elif not is_checked and name in selected_names:
        selected_names.remove(name)
        display_map.refresh()


@ui.refreshable
def display_map():
    map = current_map_object
    if len(selected_names) == 0:
        ui.label("Please select at least one run type to display.").classes(
            'text-lg text-gray-500 italic')
    else:
        with ui.row().classes(
            'justify-center w-full p-4').style('margin-top: -80px;'):
            with ui.pyplot(figsize=(10, 10)):
                plot_track(selected_names,
                           gpx_infos,
                           colors,
                           lws=lws,
                           step=2,
                           round=5,
                           with_map=True,
                           savefig=False,
                           nicegui=True,
                           map_style=map)


with ui.column().classes('items-center w-full p-4'):

    # --- Card with user/color selection and map selector in header ---
    with ui.card().classes('p-4 w-full max-w-3xl shadow-lg'):
        with ui.row().classes('justify-between items-center mb-2'):
            ui.label("User Selection & Colors").classes('text-lg font-bold')
            with ui.row().classes('items-center gap-2'):
                ui.label("Map style").classes('text-sm text-gray-600')
                ui.select(
                    options=list(MAPS_OPTIONS.keys()),
                    value=initial_selection_key,
                    on_change=handle_map_change
                ).classes('w-48')

        ui.separator()

        # Hubert section
        with ui.grid(columns=4).classes('gap-4 items-center mt-4'):
            ui.checkbox(
                'Hubert',
                value=True,
                on_change=lambda e: update_selection('hubert', e.value)
            )
            ui.label("Hubert Color").classes('text-sm text-gray-600')
            ui.select(
                options=COLORS,
                on_change=handle_hubert_color_change,
            ).classes('w-full col-span-2')

            # ui.label("Line thickness Level").classes('text-sm text-gray-600 mr-2')
            # ui.slider(
            #     min=0.5,
            #     max=10,
            #     step=1,
            #     value=1,
            #     on_change=handle_hubert_lw_change
            # ).classes('w-full')

        # Pierre-Antoine section (new grid → new row)
        with ui.grid(columns=4).classes('gap-4 items-center mt-2'):
            ui.checkbox(
                'Pierre-Antoine',
                value=False,
                on_change=lambda e: update_selection('pa', e.value)
            )
            ui.label("PA Color").classes('text-sm text-gray-600')
            ui.select(
                options=COLORS,
                on_change=handle_pa_color_change,
            ).classes('w-full col-span-2')

update_selection('hubert', True)
display_map()

ui.page.title = "Bike it"
ui.run()
