#!/bin/bash

#conda activate bikeit_env.yml
python generate_stats.py
#python app_graph.py
python -m http.server 8000 &
firefox http://localhost:8000
#firefox index.html
#Example of call for missing streets; python generate_stats.py --generate_missing_streets_district "Eixample" "Gracia" --generate_missing_streets_user "PA"
