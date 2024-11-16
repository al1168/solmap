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
        **pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"],
    )

    # Finally we put it all together:

    # We simulate the DC electricity output of our PV panel given the effective solar irradiance and cell temperature)
    dc_electricity_timeseries = pvlib.pvsystem.sapm(
        effective_irradiance_timeseries, 
        cell_temperature_timeseries, 
        pv_panel_model
    )

    # And then we simulate the inverter converting the DC output into AC output
    ac_electricity_timeseries_watts = pvlib.inverter.sandia(
        dc_electricity_timeseries["v_mp"], 
        dc_electricity_timeseries["p_mp"], 
        inverter_model
    )

    # Wrap the results all up into a dataframe for plotting!
    pv_model_results = pd.DataFrame(
        {
            "PV Array Output (Wh)": dc_electricity_timeseries["i_mp"] * dc_electricity_timeseries["v_mp"],
            "Inverter Output (Wh)": ac_electricity_timeseries_watts,
            "Solar azimuth (°)": solar_position_timeseries["azimuth"],
            "Solar elevation (°)": solar_position_timeseries["apparent_elevation"],
        }
    )
    pv_model_results["timestamp"] = pv_model_results.index.map(
        lambda utc_time: utc_time.astimezone(pytz.timezone('UTC'))
    )
    return pv_model_results


def datetime_string():
    s = (
        datetime
        .now()
        .isoformat()
        .replace('-','_')
        .replace(':','_')
        .replace('.','_')
        )
    return s


def solar_potential(lat: float, lon: float) -> float:
    """
    Take parameters specifying a real or simulated location. Return its yearly solar potential.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        [additional parameters to be implemented]

    Returns:
        generation (float): kWh/year/m2 of an optimally positioned solar panel
    """
    load_dotenv()
    NREL_API_KEY = os.getenv("NREL_API_KEY")
    NREL_API_EMAIL = os.getenv("NREL_API_EMAIL")
    try:
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
    #warnings.warn("All altitudes are set to 0.")
    pv_model_results = simulate_pv_ouptput(
        solar_weather_timeseries,
        latitude=lat,
        longitude=lon,
        altitude=0,
        pv_array_tilt=lat,
        pv_array_azimuth=180,
        pv_panel_model=PV_PANEL_MODEL,
        inverter_model=INVERTER_MODEL,
    )
    generation_kWh_year = pv_model_results["Inverter Output (Wh)"].sum() / 1000
    generation_kWh_year_m2 = generation_kWh_year / PV_PANEL_MODEL.Area
    return generation_kWh_year_m2


def generate_values_at_points(df):
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
        if i[6] % 50 == 0:
            print(f"i = {i[6]}")
        generation_list += [(point[0], point[1], solar_potential(point[0], point[1]), i[0])]
    generation_df = pd.DataFrame(generation_list, columns=["lat", "lon", "generation", "GEO_ID"]).dropna().reset_index()
    file_name = f"generation_{datetime_string()}.csv"
    generation_df.to_csv(file_name)
    print(f"Saved to {file_name}")
    return generation_df


def save_as_geojson(geo_df, solar_df):
    json_output = {"type": "FeatureCollection", "features": []}
    # currently assuming specific format for CD dataset
    # and for "real" generation
    for i, row in geo_df.iterrows():
        g = solar_df[solar_df.GEO_ID == i[0]]
        if g.shape[0] == 0:
            print(f"passing on GEO_ID {i[0]}")
            continue
        assert g.shape[0] == 1
        assert g.lat.values[0] == row.lat
        assert g.lon.values[0] == row.lon
        this_feature = {
            "type": "Feature",
            "properties": {
                "GEO_ID": i[0],
                "STATE": i[1],
                "CD": i[2],
                "NAME": i[3],
                "LSAD": i[4],
                "CENSUSAREA": i[5],
                "generation_real": g.generation.values[0],
            },
            "geometry": {"type": "Point", "coordinates": [row.lon, row.lat]},
        }
        json_output["features"] += [this_feature]
    file_name = f'solar_points_{datetime_string()}.json'
    with open(file_name, 'w') as f:
        json.dump(json_output, f)
        print(f"Saved to {file_name}")
    return True
