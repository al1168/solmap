import pvlib
import pytz
from requests import HTTPError
import pandas as pd
from datetime import datetime
import json
import os
from dotenv import load_dotenv

PV_PANEL_MODEL = pvlib.pvsystem.retrieve_sam("SandiaMod")[
    "Canadian_Solar_CS5P_220M___2009_"
]
INVERTER_MODEL = pvlib.pvsystem.retrieve_sam("cecinverter")[
    "ABB__MICRO_0_25_I_OUTD_US_208__208V_"
]

# default pvlib.iotools.psm3.ATTRIBUTES plus four more
SOLAR_WEATHER_ATTRIBUTES = (
    "air_temperature",
    "dew_point",
    "dhi",
    "clearsky_dhi",
    "dni",
    "clearsky_dni",
    "ghi",
    "clearsky_ghi",
    "surface_albedo",
    "surface_pressure",
    "wind_direction",
    "wind_speed",
)


def simulate_pv_ouptput(
    solar_weather_timeseries,
    latitude,
    longitude,
    altitude,
    pv_array_tilt,
    pv_array_azimuth,
    pv_panel_model,
    inverter_model,
):
    # This function taken from week 4 assigment
    # We're using `pvlib` to simulate how much electricity our PV system would generate given historical "solar weather" data

    # Adapted from example: https://pvlib-python.readthedocs.io/en/v0.9.0/introtutorial.html?highlight=total_irradiance#procedural
    # new link: https://pvlib-python.readthedocs.io/en/v0.11.1/user_guide/introtutorial.html

    # First, we model the position of the sun relative to our chosen location over the simulation year
    solar_position_timeseries = pvlib.solarposition.get_solarposition(
        time=solar_weather_timeseries.index,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        temperature=solar_weather_timeseries["temp_air"],
    )

    # We combine solar position with historical solar weather data to model total irradiance for our PV panel
    total_irradiance_timeseries = pvlib.irradiance.get_total_irradiance(
        pv_array_tilt,
        pv_array_azimuth,
        solar_position_timeseries["apparent_zenith"],
        solar_position_timeseries["azimuth"],
        solar_weather_timeseries["dni"],
        solar_weather_timeseries["ghi"],
        solar_weather_timeseries["dhi"],
        dni_extra=pvlib.irradiance.get_extra_radiation(solar_weather_timeseries.index),
        model="haydavies",
    )

    # We then model air mass & angle of incidence, which we combine with total irradiance to model "effective" irradiance on our PV panel
    # Air mass is a measure of the path length of solar radiation through the atmosphere
    absolute_airmass_timeseries = pvlib.atmosphere.get_absolute_airmass(
        pvlib.atmosphere.get_relative_airmass(
            solar_position_timeseries["apparent_zenith"]
        ),
        pvlib.atmosphere.alt2pres(altitude),
    )

    # Angle of incidence is the angle of the sun's rays relative to the panel's surface
    angle_of_incidence_timeseries = pvlib.irradiance.aoi(
        pv_array_tilt,
        pv_array_azimuth,
        solar_position_timeseries["apparent_zenith"],
        solar_position_timeseries["azimuth"],
    )

    # This is where we combine the direct and diffuse irradiance, taking into account the air mass that the sunlight has to travel through
    effective_irradiance_timeseries = pvlib.pvsystem.sapm_effective_irradiance(
        total_irradiance_timeseries["poa_direct"],
        total_irradiance_timeseries["poa_diffuse"],
        absolute_airmass_timeseries,
        angle_of_incidence_timeseries,
        pv_panel_model,
    )

    # We model the temperature within the PV panel ("cell temperature"), which affects the efficiency of the panels
    cell_temperature_timeseries = pvlib.temperature.sapm_cell(
        total_irradiance_timeseries["poa_global"],
        solar_weather_timeseries["temp_air"],
        solar_weather_timeseries["wind_speed"],
        **pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"][
            "open_rack_glass_glass"
        ],
    )

    # Finally we put it all together:

    # We simulate the DC electricity output of our PV panel given the effective solar irradiance and cell temperature)
    dc_electricity_timeseries = pvlib.pvsystem.sapm(
        effective_irradiance_timeseries, cell_temperature_timeseries, pv_panel_model
    )

    # And then we simulate the inverter converting the DC output into AC output
    ac_electricity_timeseries_watts = pvlib.inverter.sandia(
        dc_electricity_timeseries["v_mp"],
        dc_electricity_timeseries["p_mp"],
        inverter_model,
    )

    # Wrap the results all up into a dataframe for plotting!
    pv_model_results = pd.DataFrame(
        {
            "PV Array Output (Wh)": dc_electricity_timeseries["i_mp"]
            * dc_electricity_timeseries["v_mp"],
            "Inverter Output (Wh)": ac_electricity_timeseries_watts,
            "Solar azimuth (°)": solar_position_timeseries["azimuth"],
            "Solar elevation (°)": solar_position_timeseries["apparent_elevation"],
        }
    )
    pv_model_results["timestamp"] = pv_model_results.index.map(
        lambda utc_time: utc_time.astimezone(pytz.timezone("UTC"))
    )
    return pv_model_results


def datetime_string():
    s = datetime.now().isoformat().replace("-", "_").replace(":", "_").replace(".", "_")
    return s


def solar_potential(
    lat: float,
    lon: float,
    use_local_cache: bool,
    save_local_cache: bool,
    cloud_adjustments: pd.DataFrame = None,
    limit_query: str = None,
    pv_array_tilt: float = None,
) -> float:
    """
    Take parameters specifying a real or simulated location. Return its yearly solar potential.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        generation (float): kWh/year/m2 of an optimally positioned solar panel
    """
    if pv_array_tilt is None:
        pv_array_tilt = lat
    solar_weather_cache_file_name = (
        f"solar_local_cache/solar_weather_lat{lat}_lon{lon}.csv"
    )
    pv_cache_file_name = f"solar_local_cache/pv_lat{lat}_lon{lon}.csv"
    if use_local_cache:
        try:
            solar_weather_timeseries = pd.read_csv(
                solar_weather_cache_file_name, index_col=0
            )
            pv_model_results = pd.read_csv(pv_cache_file_name, index_col=0)
            for d in [solar_weather_timeseries, pv_model_results]:
                d.index = pd.to_datetime(d.index)
        except:
            print(f"Cache miss at {lat}, {lon}: computing from scratch.")
            return solar_potential(
                lat,
                lon,
                False,
                save_local_cache,
                cloud_adjustments,
                limit_query,
                pv_array_tilt,
            )
    else:
        try:
            load_dotenv()
            NREL_API_KEY = os.getenv("NREL_API_KEY")
            NREL_API_EMAIL = os.getenv("NREL_API_EMAIL")
            solar_weather_timeseries, solar_weather_metadata = pvlib.iotools.get_psm3(
                latitude=lat,
                longitude=lon,
                names=2019,
                leap_day=False,
                attributes=SOLAR_WEATHER_ATTRIBUTES,
                map_variables=True,
                api_key=NREL_API_KEY,
                email=NREL_API_EMAIL,
            )
        except HTTPError:
            print(f"Missing solar weather for {lat}, {lon}")
            return None
        except:
            print(f"Other error for {lat}, {lon}")
            return None
        # warnings.warn("All altitudes are set to 0.")
        pv_model_results = simulate_pv_ouptput(
            solar_weather_timeseries,
            latitude=lat,
            longitude=lon,
            altitude=0,
            pv_array_tilt=pv_array_tilt,
            pv_array_azimuth=180,
            pv_panel_model=PV_PANEL_MODEL,
            inverter_model=INVERTER_MODEL,
        )
    if cloud_adjustments is not None:
        assert cloud_adjustments.shape[0] == solar_weather_timeseries.shape[0]
        solar_weather_timeseries_mod = solar_weather_timeseries.copy().reset_index()
        solar_weather_timeseries_mod = (
            solar_weather_timeseries_mod.rename(
                columns={"dhi": "dhi_orig", "dni": "dni_orig", "ghi": "ghi_orig"}
            )
            .assign(dhi_adj=cloud_adjustments.reset_index().dhi_adj)
            .assign(dni_adj=cloud_adjustments.reset_index().dni_adj)
            .assign(ghi_adj=cloud_adjustments.reset_index().ghi_adj)
            .set_index(solar_weather_timeseries.index)
        )
        solar_weather_timeseries_mod = solar_weather_timeseries_mod.assign(
            dhi=(
                solar_weather_timeseries_mod.dhi_clear
                * solar_weather_timeseries_mod.dhi_adj
            ).fillna(solar_weather_timeseries_mod.dhi_orig),
            dni=(
                solar_weather_timeseries_mod.dni_clear
                * solar_weather_timeseries_mod.dni_adj
            ).fillna(solar_weather_timeseries_mod.dni_orig),
            ghi=(
                solar_weather_timeseries_mod.ghi_clear
                * solar_weather_timeseries_mod.ghi_adj
            ).fillna(solar_weather_timeseries_mod.ghi_orig),
        )
        solar_weather_timeseries = solar_weather_timeseries_mod
    if cloud_adjustments is not None or pv_array_tilt is not None:
        pv_model_results_mod = simulate_pv_ouptput(
            solar_weather_timeseries,
            latitude=lat,
            longitude=lon,
            altitude=0,
            pv_array_tilt=pv_array_tilt,
            pv_array_azimuth=180,
            pv_panel_model=PV_PANEL_MODEL,
            inverter_model=INVERTER_MODEL,
        )
        assert pv_model_results_mod.shape == pv_model_results.shape
        pv_model_results = pv_model_results_mod
    if limit_query is not None:
        pv_model_results = pv_model_results.query(limit_query)
    generation_kWh_year = pv_model_results["Inverter Output (Wh)"].sum() / 1000
    generation_kWh_year_m2 = generation_kWh_year / PV_PANEL_MODEL.Area
    if save_local_cache and not use_local_cache:
        solar_weather_timeseries.to_csv(solar_weather_cache_file_name)
        print(f"Wrote {solar_weather_cache_file_name}")
        pv_model_results.to_csv(pv_cache_file_name)
        print(f"Wrote {pv_cache_file_name}")
    return generation_kWh_year_m2


def generate_values_at_points(
    df,
    pv_array_tilt=None,
):
    """
    Args:
        df (pd.DataFrame): points to fetch solar potential at

    Returns:
        generation_df (float): kWh/year/m2 at each point
    """
    generation_list = []
    for i, row in df.iterrows():
        # currently assuming specific format for CD dataset
        point = (row.lat, row.lon)
        if i[6] % 100 == 0:
            print(f"i = {i[6]}")
        solar_generation_value = solar_potential(
            point[0],
            point[1],
            use_local_cache=True,
            save_local_cache=True,
            pv_array_tilt=pv_array_tilt,
        )
        generation_list += [(point[0], point[1], solar_generation_value, i[0])]
    generation_df = (
        pd.DataFrame(generation_list, columns=["lat", "lon", "generation", "GEO_ID"])
        .dropna()
        .reset_index()
    )
    file_name = f"generation_{datetime_string()}.csv"
    generation_df.to_csv(file_name)
    print(f"Saved to {file_name}")
    return generation_df


def save_as_geojson(geo_df, solar_df_dict):
    json_output = {"type": "FeatureCollection", "features": []}
    # currently assuming specific format for CD dataset
    # and for "real" generation
    missing_value_count = 0
    for i, row in geo_df.iterrows():
        value_dict = {}
        for solar_name, solar_df in solar_df_dict.items():
            g = solar_df[solar_df.GEO_ID == i[0]]
            if g.shape[0] == 0:
                missing_value_count += 1
                value = None
            else:
                assert g.shape[0] == 1
                assert g.lat.values[0] == row.lat
                assert g.lon.values[0] == row.lon
                value = g.generation.values[0]
            value_dict[solar_name] = value
        this_feature = {
            "type": "Feature",
            "properties": {
                "GEO_ID": i[0],
                "STATE": i[1],
                "CD": i[2],
                "NAME": str(i[3]),
                "LSAD": i[4],
                "CENSUSAREA": i[5],
            }
            | value_dict,
            "geometry": {"type": "Point", "coordinates": [row.lon, row.lat]},
        }
        json_output["features"] += [this_feature]
    if missing_value_count > 0:
        print(f"Missing values for {missing_value_count} geos, continuing.")
    file_name = f"solar_points_{datetime_string()}.json"
    with open(file_name, "w") as f:
        json.dump(json_output, f)
        print(f"Saved to {file_name}")
    return True


def simulate_for_constant_clouds(
    lat_source,
    lon_source,
    geo_df,
    limit_query=None,
    pv_array_tilt=None,
):
    if pv_array_tilt is None:
        pv_array_tilt = lat_source
    solar_weather_cache_file_name_source = (
        f"solar_local_cache/solar_weather_lat{lat_source}_lon{lon_source}.csv"
    )
    solar_weather_timeseries_source = pd.read_csv(
        solar_weather_cache_file_name_source,
        index_col=0,
    )
    solar_weather_timeseries_source.index = pd.to_datetime(
        solar_weather_timeseries_source.index
    )
    cloud_adjustments = solar_weather_timeseries_source[
        [
            "dhi",
            "dhi_clear",
            "dni",
            "dni_clear",
            "ghi",
            "ghi_clear",
        ]
    ].copy()
    cloud_adjustments = (
        cloud_adjustments.assign(
            dhi_adj=cloud_adjustments.dhi / cloud_adjustments.dhi_clear
        )
        .assign(dni_adj=cloud_adjustments.dni / cloud_adjustments.dni_clear)
        .assign(ghi_adj=cloud_adjustments.ghi / cloud_adjustments.ghi_clear)
    )
    generation_list = []
    for i, row in geo_df.iterrows():
        # currently assuming specific format for CD dataset
        point = (row.lat, row.lon)
        if i[6] % 100 == 0:
            print(f"i = {i[6]}")
        solar_generation_value = solar_potential(
            point[0],
            point[1],
            use_local_cache=True,
            save_local_cache=False,
            cloud_adjustments=cloud_adjustments,
            limit_query=limit_query,
            pv_array_tilt=pv_array_tilt,
        )
        generation_list += [(point[0], point[1], solar_generation_value, i[0])]
    generation_df = (
        pd.DataFrame(generation_list, columns=["lat", "lon", "generation", "GEO_ID"])
        .dropna()
        .reset_index()
    )
    file_name = f"generation_clouds_matching_lat{lat_source}_lon{lon_source}_tilt{pv_array_tilt}_{datetime_string()}.csv"
    generation_df.to_csv(file_name)
    print(f"Saved to {file_name}")
    return generation_df


def make_timeseries(lat, lon):
    pv_detail = pd.read_csv(
        f"solar_local_cache/pv_lat{lat}_lon{lon}.csv",
        index_col=0,
        parse_dates=["timestamp"],
    )
    pv_detail = pv_detail.assign(date=pv_detail.timestamp.dt.date)
    pv_detail = pv_detail.assign(
        week=pd.to_datetime(pv_detail.date).dt.to_period("W-MON")
    )
    pv_summary = (
        pv_detail.groupby("date", as_index=False)
        .agg(
            date_energy=("Inverter Output (Wh)", "sum"),
            date_count=("Inverter Output (Wh)", "count"),
            date_std=("Inverter Output (Wh)", "std"),
            week=("week", "min"),
        )
        .groupby("week")
        .agg(
            energy_per_day=("date_energy", "mean"),
            day_count=("date_energy", "count"),
            energy_per_day_std=("date_energy", "std"),
        )
        .head(52)
    )
    pv_summary = pv_summary.assign(
        energy_uncert_hi=pv_summary.energy_per_day + pv_summary.energy_per_day_std,
        energy_uncert_lo=pv_summary.energy_per_day - pv_summary.energy_per_day_std,
    )
    ax = pv_summary.plot(
        y=["energy_per_day"],
    )
    ax.fill_between(
        pv_summary.index,
        pv_summary.energy_uncert_hi,
        pv_summary.energy_uncert_lo,
        alpha=0.3,
    )
    ax.set_ylim([0, (pv_summary.energy_per_day + pv_summary.energy_per_day_std).max()])
    ax.set_title(f"{lat:0.5f}, {lon:0.5f}")
    file_name = f"timeseries_lat{lat}_lon{lon}.csv"
    pv_summary.to_csv(file_name)
    print(f"Werote {file_name}")
    return ax
