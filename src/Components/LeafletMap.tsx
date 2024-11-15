// import { Feature } from "geojson";
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, useMap, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIconPng from "leaflet/dist/images/marker-icon.png";
import markerShadowPng from "leaflet/dist/images/marker-shadow.png";
import statesData from "../Constants/congstates";
import generation_points from "../Constants/real_generation_points";
import mergeGeoJSONByID from "../Lib/Map/mergeGeoJSON";
import fipsToState from "../Constants/FipsCodeToStateName";
let DefaultIcon = L.icon({
  iconUrl: markerIconPng,
  shadowUrl: markerShadowPng,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

const usBounds = L.latLngBounds(
  [24.396308, -125.0], // Southwest corner
  [49.384358, -66.93457] // Northeast corner
);

function getColor(d: number): string {
  return d > 270
    ? "#FF0000" // Bright red
    : d > 250
    ? "#FF4500" // Orange-red
    : d > 230
    ? "#FFA500" // Orange
    : d > 210
    ? "#FFD700" // Gold
    : d > 190
    ? "#FFFF00" // Yellow
    : d > 170
    ? "#87CEEB" // Sky blue
    : "#0000FF"; // Deep blue
}

function style(feature: any) {
  return {
    fillColor: getColor(feature.properties.generation_real),
    weight: 2.5,
    // opacity: 1,
    color: "black",
    // dashArray: "3",
    fillOpacity: 0.7,
  };
}

function highlightFeature(e: L.LeafletMouseEvent) {
  const layer = e.target;

  layer.setStyle({
    weight: 10,
    color: "purple",
    // dashArray: "",
    // fillOpacity: 0.7,
  });

  const { generation_real, CD, STATE } = layer.feature.properties;
  layer.bindTooltip(
    `<strong> District: ${CD}, ${fipsToState[Number(STATE)]}</strong><br>Generation Real: ${generation_real}`,
    {
      permanent: false,
      direction: "top",
      offset: L.point(0, -10),
      className: "custom-tooltip"
    }
  ).openTooltip(e.latlng);


}

function resetHighlight(e: L.LeafletMouseEvent) {
  const layer = e.target;
  layer.setStyle(style(layer.feature));
}

function LeafletMap() {
  const [data, setData] = useState<any>(statesData);
  useEffect(() => {
    // add points to polygon
    // @ts-ignore
    const merged_data = mergeGeoJSONByID(statesData, generation_points);
    setData(merged_data);
  }, []);
  function onEachFeature(feature: any, layer: L.Layer) {
    layer.on({
      mouseover: highlightFeature,
      mouseout: resetHighlight,
      click: (e) => {
        console.log("Clicked feature:", feature);
        console.log("Feature properties:", feature.properties);

        const generationReal = feature.properties.generation_real;
        console.log("Generation Real:", generationReal);

      },
    });
  }

  function handleMapClick(event: any) {
    console.log(event);
    // generate graph based on feature
  }

  function HandleResizeAndClick() {
    const map = useMap();

    useEffect(() => {
      map.invalidateSize(); 
      map.on("click", handleMapClick);

      return () => {
        map.off("click", handleMapClick);
      };
    }, [map]);

    return null;
  }

  return (
    <MapContainer
      style={{ height: "100vh", width: "100%" }}
      center={[38.7946, -106.5348]}
      zoom={5}
      scrollWheelZoom={true}
      // maxBounds={usBounds}
      // minZoom={4}
      // maxZoom={6}
    >
      <HandleResizeAndClick />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON
        key={JSON.stringify(data)}
        data={data}
        style={style}
        onEachFeature={onEachFeature}
      />
    </MapContainer>
  );
}

export default LeafletMap;
// Option 1: apply cloud distro on rest of states when clicking on central texas
// precomputed data to display

// Option 2: graph/change map when clicking state to see time series of how much sun/`energy generated

// todo:
// generate data for el paso nyc manhattan seattle

// cloud distrobution swap between properties

// blue purple dark - low end

// yellow orange bright red - highend
