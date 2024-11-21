import json

import numpy as np
import pandas as pd

LAT_SAN_FRANCISCO = 37.78128901022419
LON_SAN_FRANCISCO = -122.4589148156449


def arbitrary_coords_lists_to_array(coords, verbose=False):
    """
    TODO 1: consider Claude suggestions
    https://claude.ai/chat/3b92403f-91c5-410d-8090-810a1c92aa82
    TODO 2: use this helper in other main functions
    GeoJSON polygons from the internet are in inconsistently formatted
    lists of lists of lists (of lists). We want a simple array of shape (N, 2).
    This flattens such an array.
    """
    if verbose:
        print(f"Starting {len(coords)=}")
    flat = []
    for item in coords:
        if verbose:
            print(f"    Processing {len(item)=}")
        subitem_lengths_all_2 = all([len(i) == 2 for i in item])
        subsubitems_all_floats = all(
            [all([isinstance(j, (float, int)) for j in i]) for i in item]
        )
        if verbose:
            print(f"    {subitem_lengths_all_2=}, {subsubitems_all_floats=}")
        if subitem_lengths_all_2 and subsubitems_all_floats:
            if verbose:
                print(f"        Appending item {len(item)=}")
            for pair in item:
                flat.append(pair)
        else:
            if verbose:
                print("        Recursive call")
            flat.extend(arbitrary_coords_lists_to_array(item, verbose=verbose))
    return flat


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
        if verbose and i % 100 == 0:
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
        congressional_df["geometry_name"] = (
            "country_usa-state_"
            + congressional_df.STATE
            + "-district_cd"
            + congressional_df.CD
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
            index_col=[
                "geometry_name",
            ],
        )
        return congressional_summary_df
    congressional_df = load_congresional_district_polygons(limit, verbose)
    congressional_summary_df = (
        congressional_df.groupby(["geometry_name"])
        .agg({"lat": "mean", "lon": "mean", "json_index": "min", "GEO_ID": "min"})
        .sort_values("json_index")
    )
    congressional_summary_df = congressional_summary_df.rename(
        columns={"GEO_ID": "json_key_value"}
    )
    congressional_summary_df["json_key_name"] = "GEO_ID"
    congressional_summary_df["lat"] = (
        congressional_summary_df["lat"].astype(float).round(1)
    )
    congressional_summary_df["lon"] = (
        congressional_summary_df["lon"].astype(float).round(1)
    )
    if file_to_save is not None:
        congressional_summary_df.to_csv(file_to_save)
        print(f"Wrote to {file_to_save}")
    return congressional_summary_df


def load_mexico_district_points(
    verbose=True,
    file_to_load=None,
    file_to_save=None,
):
    """
    Args:
        limit (int): max number of geometries processes
        verbose (bool): print progress?

    Returns:
        df (pd.DataFrame): CDs in DataFrame format, one row per polygon vertex point
    """
    # This json of Mexican municipality boundries comes from
    # https://github.com/PhantomInsights/mexico-geojson
    # year = 2022
    if file_to_load is not None:
        mexico_df = pd.read_csv(
            file_to_load,
            index_col=[
                "geometry_name",
            ],
        )
        return mexico_df
    with open("mexico.json", "r") as f:
        mexico_json = json.load(f)
    mexico_dict = {
        "geometry_name": [],
        "lat": [],
        "lon": [],
        "json_key_value": [],
        "json_key_name": [],
    }
    for feature in mexico_json["features"]:
        properties = feature["properties"]
        geometry_name = (
            "country_mexico-state_"
            + properties["NOM_ENT"]
            + "-district_"
            + properties["NOMGEO"]
        )
        coordinates = feature["geometry"]["coordinates"]
        try:
            c_array = np.array(coordinates)[0]
        except ValueError:
            coordinates_munged = []
            for c in coordinates:
                if len(c) == 1:
                    coordinates_munged += c[0]
                else:
                    coordinates_munged += c
            try:
                c_array = np.array(coordinates_munged)
            except ValueError:
                print(f"Not bothering with {geometry_name}")
        assert c_array.ndim == 2
        assert c_array.shape[0] >= 3
        assert c_array.shape[1] == 2
        # Note the order
        lon, lat = c_array.mean(axis=0).round(1).tolist()
        mexico_dict["geometry_name"] += [geometry_name]
        mexico_dict["lat"] += [lat]
        mexico_dict["lon"] += [lon]
        mexico_dict["json_key_value"] += [properties["CVEGEO"]]
        mexico_dict["json_key_name"] += ["CVEGEO"]
    mexico_df = pd.DataFrame(mexico_dict)
    mexico_df = mexico_df.groupby("geometry_name").first()
    if file_to_save is not None:
        mexico_df.to_csv(file_to_save)
        print(f"Wrote to {file_to_save}")
    return mexico_df
