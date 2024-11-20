import { useCallback, useEffect, useState, useMemo } from "react";
import { MapContainer, TileLayer, useMap, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIconPng from "leaflet/dist/images/marker-icon.png";
import markerShadowPng from "leaflet/dist/images/marker-shadow.png";
import statesData from "../Constants/congstates";
import mergeGeoJSONByID from "../Lib/Map/mergeGeoJSON";
import solardata from "../Constants/Solardata";
import fipsToState from "../Constants/FipsCodeToStateName";
import * as d3 from "d3-scale";
import { interpolateTurbo } from "d3-scale-chromatic";
import {
  RadioGroup,
  Radio,
  Select,
  SelectItem,
  Avatar,
} from "@nextui-org/react";
let DefaultIcon = L.icon({
  iconUrl: markerIconPng,
  shadowUrl: markerShadowPng,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

function LeafletMap() {
  const [data, setData] = useState<any>(statesData);
  const [baseFactor, setBaseFactor] = useState<string>("generation_real");
  const [viewMode, setViewMode] = useState<string>("tilted");
  const [finalFactor, setFinalFactor] = useState<string>(
    baseFactor + (viewMode === "horizontal" ? "_horizontal" : "")
  );

  useEffect(() => {
    // add points to polygon
    // @ts-ignore
    const merged_data = mergeGeoJSONByID(statesData, solardata);
    setData(merged_data);
  }, []);

  const usBounds = L.latLngBounds(
    [24.396308, -125.0], // Southwest corner
    [49.384358, -66.93457] // Northeast corner
  );

  // Create a dynamic color scale for smoother transitions
  const colorScale = d3.scaleSequential(interpolateTurbo).domain([170, 270]);

  useEffect(() => {
    setFinalFactor(
      baseFactor + (viewMode === "horizontal" ? "_horizontal" : "")
    );
  }, [baseFactor, viewMode]);

  const style = useCallback(
    (feature: any) => {
      function getColor(d: number): string {
        const clampedValue = Math.min(Math.max(d, 140), 270);
        return colorScale(clampedValue).toString();
      }

      const property = feature.properties[finalFactor];
      return {
        fillColor: getColor(property || 0),
        weight: 2.5,
        color: "black",
        fillOpacity: 0.7,
      };
    },
    [finalFactor]
  );
  function highlightFeature(e: L.LeafletMouseEvent) {
    const layer = e.target;

    layer.setStyle({
      weight: 10,
      color: "purple",
    });

    const { CD, STATE } = layer.feature.properties;
    const generationValue = layer.feature.properties[finalFactor] ?? "Unknown";

    layer
      .bindTooltip(
        `<strong> District: ${CD}, ${
          fipsToState[Number(STATE)]
        }</strong><br>${finalFactor}: ${generationValue} KWHs`,
        {
          permanent: false,
          direction: "top",
          offset: L.point(0, -10),
          className: "custom-tooltip",
        }
      )
      .openTooltip(e.latlng);
  }

  const resetHighlight = useCallback(
    (e: L.LeafletMouseEvent) => {
      const layer = e.target;
      const feature = layer.feature;
      layer.setStyle(style(feature));
    },
    [style]
  );

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

  const Legend = ({
    colorScale,
  }: {
    colorScale: d3.ScaleSequential<string, never>;
  }) => {
    const map = useMap();

    useEffect(() => {
      const legendControl = new L.Control({ position: "bottomright" });

      legendControl.onAdd = () => {
        const div = L.DomUtil.create(
          "div",
          "info legend bg-white p-4 rounded shadow-md text-gray-700 text-sm"
        );
        const [min, max] = colorScale.domain(); // Get the scale domain
        const steps = 6; // Number of legend steps
        const ticks = Array.from(
          { length: steps + 1 },
          (_, i) => min + (i * (max - min)) / steps
        );
        const labels = ticks.map(
          (tick: d3.NumberValue) =>
            `<div class="flex items-center mb-1">
              <span class="inline-block w-5 h-5 mr-2 rounded-sm" style="background:${colorScale(
                tick
              )};"></span>
              <span>${Math.round(Number(tick))}</span>
            </div>`
        );

        // Add title and labels
        div.innerHTML = `
          <h4 class="font-semibold mb-2">Legend</h4>
          ${labels.join("")}
          <h4 class="font-semibold mb-2"> Kilowatt Hours</h4>
        `;
        return div;
      };

      legendControl.addTo(map);

      return () => {
        legendControl.remove();
      };
    }, [map, colorScale]);

    return null;
  };

  return (
    <div className="flex-col">
      <div>
        <Select
          className="max-w-xs"
          label="Select a State"
          onSelectionChange={(key) =>
            setBaseFactor(Array.from(key)[0] as string)
          }
        >
          <SelectItem
            key="generation_real"
            startContent={
              <Avatar
                alt="USA"
                className="w-6 h-6"
                src="https://flagcdn.com/us.svg"
              />
            }
          >
            No State
          </SelectItem>
          <SelectItem
            key="generation_texas_clouds"
            startContent={
              <Avatar
                alt="Texas"
                className="w-6 h-6"
                src="https://flagcdn.com/us-tx.svg"
              />
            }
          >
            Texas
          </SelectItem>
          <SelectItem
            key="generation_ny_clouds"
            startContent={
              <Avatar
                alt="NY"
                className="w-6 h-6"
                src="https://flagcdn.com/us-ny.svg"
              />
            }
          >
            New York
          </SelectItem>
          <SelectItem
            key="generation_wash_clouds"
            startContent={
              <Avatar
                alt="Washington"
                className="w-6 h-6"
                src="https://flagcdn.com/us-wa.svg"
              />
            }
          >
            Washington
          </SelectItem>
        </Select>

        <div>
          <RadioGroup
            label="Orientation"
            orientation="horizontal"
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value)}
          >
            <Radio value="tilted">Tilted</Radio>
            <Radio value="horizontal">Horizontal</Radio>
          </RadioGroup>
        </div>
      </div>

      <MapContainer
        center={[38.76265, -94.396089]}
        zoom={5}
        scrollWheelZoom={true}
        className="border-double border-5 border-indigo-500 rounded-xl w-[80vw] h-[80vh]"
        // maxBounds={usBounds}
        minZoom={4}
      >
        <HandleResizeAndClick />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Legend colorScale={colorScale} />
        <GeoJSON
          key={finalFactor}
          data={data}
          style={style}
          onEachFeature={onEachFeature}
        />
      </MapContainer>
    </div>
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
