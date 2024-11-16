import json
import numpy as np
import pandas as pd

LAT_SAN_FRANCISCO = 37.78128901022419
LON_SAN_FRANCISCO = -122.4589148156449


def load_congresional_district_polygons(limit=None, verbose=True):
	"""
    Args:
        limit (int): max number of geometries processes
        verbose (bool): print progress?

    Returns:
        congressional_df (pd.DataFrame): CDs in DataFrame format, one row per polygon vertex point
	"""
	# This json of congressional district boundries comes from
	# https://eric.clst.org/tech/usgeojson/
	with open("gz_2010_us_500_11_20m.json", "r") as f:
	    congressional_json = json.load(f)
	congressional_df = pd.DataFrame()
	for i, feature in enumerate(congressional_json["features"]):
	    if verbose and i % 50 == 0:
	        print(f"i = {i}")
	    if limit is not None and i >= limit:
	        break
	    property_dict = feature["properties"]
	    property_dict["json_index"] = i
	    property_row = pd.Series(property_dict)
	    coordinates_list = feature["geometry"]["coordinates"]
	    if len(coordinates_list) == 1:
	        coordinates_array = np.array(coordinates_list[0])
	    else:
	        coordinates_list_of_lists = []
	        for sub_list in coordinates_list:
	            if len(sub_list) == 1 or i == 83:
	                # CD 83 has another layer, just throwing aways the second polygon
	                # because I can't be bothered
	                # One can imagine a better solution than this hack
	                sub_list = sub_list[0]
	            else:
	                # The occasional case when there's one fewer dimension.
	                pass
	            coordinates_list_of_lists += [sub_list]
	        coordinates_array = np.concatenate(coordinates_list_of_lists)
	    full_row_list = []
	    for coord in coordinates_array:
	        full_row = pd.concat(
	            [property_row, pd.Series({"lat": coord[1], "lon": coord[0]})]
	        )
	        full_row_list += [full_row]
	    congressional_df = pd.concat(
	        [congressional_df] + [r.to_frame().T for r in full_row_list]
	    )
	return congressional_df


def load_congresional_district_points(
	limit=None,
	verbose=True,
	file_to_load=None,
	file_to_save=None,
	):
	"""
    Args:
        limit (int): max number of geometries processes
        verbose (bool): print progress?
        file_to_load (str): local csv file to use
        file_to_save (srt): compute and then save to local csv

    Returns:
        congressional_summary_df (pd.DataFrame): CDs in DataFrame format, one row per CD
	"""
	if file_to_load is not None:
		congressional_summary_df = pd.read_csv(
			file_to_load,
			index_col=['GEO_ID', 'STATE', 'CD', 'NAME', 'LSAD', 'CENSUSAREA', 'json_index'],
			dtype={
				"GEO_ID":         "object",
				"STATE":          "object",
				"CD":             "object",
				"NAME":           "object",
				"LSAD":           "object",
				"CENSUSAREA":    "float64",
				"json_index":      "int64",
				"lat":           "float64",
				"lon":           "float64",
			}
			)
		return congressional_summary_df
	congressional_df = load_congresional_district_polygons(limit, verbose)
	congressional_summary_df = (
	    congressional_df.groupby(
	        ["GEO_ID", "STATE", "CD", "NAME", "LSAD", "CENSUSAREA", "json_index"]
	    )
	    .agg({"lat": "mean", "lon": "mean"})
	    .sort_values("json_index")
	    )
	if file_to_save is not None:
		congressional_summary_df.to_csv(file_to_save)
		print(f"Wrote to {file_to_save}")
	return congressional_summary_df

