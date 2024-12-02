import { useCallback, useEffect, useState, } from "react";
import {
  MapContainer,
  TileLayer,
  useMap,
  GeoJSON,
  Marker,
  Popup,
} from "react-leaflet";
import L, { LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import markerShadowPng from "leaflet/dist/images/marker-shadow.png";
import statesData from "../Constants/congstates";
import mergeGeoJSONByID from "../Lib/Map/mergeGeoJSON";
import solardata from "../Constants/Solardata";
import fipsToState from "../Constants/FipsCodeToStateName";
import * as d3 from "d3-scale";
import { interpolateTurbo } from "d3-scale-chromatic";
import orangeMarker from "../Assets/location-pin.png";
import Joyride from "react-joyride";
import {
  RadioGroup,
  Radio,
  Select,
  SelectItem,
  Avatar,
} from "@nextui-org/react";
import EnergyChart from "../Lib/EnergyChart";
let DefaultIcon = L.icon({
  iconUrl: orangeMarker,
  shadowUrl: markerShadowPng,
  iconSize: [30, 30],
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
  const [selectedMarker, setSelectedMarker] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(5);
  const [runTour, setRunTour] = useState(true);
  const handleMarkerClick = (id: string) => {
    setSelectedMarker(id);
  };
  const markersData = [
    {
      id: "arizona",
      position: [32.05526076086956, -110.2840603695652] as LatLngExpression,
      csvPath: `${process.env.PUBLIC_URL}/csv/Arizona_timeseries.csv`,
      label: "Arizona",
    },
    {
      id: "newYork",
      position: [40.80584118750001, -73.92918853124999] as LatLngExpression,
      csvPath: `${process.env.PUBLIC_URL}/csv/new_york_timeseries.csv`,
      label: "New York",
    },
    {
      id: "washington",
      position: [47.50261456060606, -122.41468303030304] as LatLngExpression,
      csvPath: `${process.env.PUBLIC_URL}/csv/wash_timeseries.csv`,
      label: "Washington",
    },
  ];
  const selectedMarkerData = markersData.find(
    (marker) => marker.id === selectedMarker
  );
  const tourSteps = [
    {
      target: '.cloud-coverage-selector',
      content: 'Select different cloud coverage scenarios, making the entire country have the same weather as a specific real location. How does this affect solar generation?',
      disableBeacon: true,
      placement: 'right' as const
    },
    {
      target: '.panel-orientation',
      content: 'Toggle between tilted and horizontal solar panel orientations to compare energy generation',
      disableBeacon: true,
      placement: 'right' as const
    },
    {
      target: '.map-container',
      content: 'Hover over districts to see detailed solar generation data. Click markers to view energy production charts.',
      disableBeacon: true,
    },
    {
      target: '.legend-container',
      content: 'This scale shows the range of solar energy generation in kilowatt hours / year / m2',
      disableBeacon: true,
      placement: 'right' as const
    }
  ];
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

  const colorScale = d3.scaleSequential(interpolateTurbo).domain([145, 265]);

  useEffect(() => {
    setFinalFactor(
      baseFactor + (viewMode === "horizontal" ? "_horizontal" : "")
    );
  }, [baseFactor, viewMode]);

  const style = useCallback(
    (feature: any) => {
      function getColor(d: number): string {
        const clampedValue = Math.min(Math.max(d, 130), 270);
        return colorScale(clampedValue).toString();
      }

      const property = feature.properties[finalFactor];
      return {
        fillColor: getColor(property || 0),
        weight: 1,
        color: "black",
        fillOpacity: 0.7,
      };
    },
    [finalFactor]
  );
  let openTooltip: L.Tooltip | null = null;
  function highlightFeature(e: L.LeafletMouseEvent) {
    const layer = e.target;

    layer.setStyle({
      weight: 10,
      color: "purple",
    });

    const { CD, STATE } = layer.feature.properties;
    const generationValue = layer.feature.properties[finalFactor] ?? "Unknown";
    if (openTooltip) {
      openTooltip.remove();
    }
    const tooltip = layer
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
    openTooltip = tooltip.getTooltip();
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
      const handleZoom = () => {
        setZoomLevel(map.getZoom());
        console.log(zoomLevel);
      };

      handleZoom();
      map.invalidateSize();

      map.on("zoomend", handleZoom);

      return () => {
        map.off("zoomend", handleZoom);
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
          "info legend bg-white p-4 rounded shadow-md text-gray-700 text-sm legend-container"
        );

        const [min, max] = colorScale.domain();
        const gradientSteps = 100;
        const gradient = Array.from({ length: gradientSteps + 1 }, (_, i) => {
          const value = min + (i * (max - min)) / gradientSteps;
          return colorScale(value);
        }).join(",");

        div.innerHTML = `
          <div class="">
          <h4 class="font-semibold mb-2">Kilowatt hours</h4>
          <div class="relative w-full h-4 mb-4">
            <div
              class="w-full h-full"
              style="background: linear-gradient(to right, ${gradient});"
            ></div>
          </div>
          <div class="flex justify-between text-xs gap-10">
            <span>${Math.round(min)}</span>
            <span>${Math.round((min + max) / 2)}</span>
            <span>${Math.round(max)}</span>
          </div>
          </div>
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

  const getPopupSize = (zoom: number) => {
    if (zoom <= 4) return "w-[350px] h-[300px]";
    if (zoom <= 5) return "w-[450px] h-[350px]";
    if (zoom <= 6) return "w-[550px] h-[400px]";
    if (zoom <= 7) return "w-[650px] h-[450px]";
    return "w-[750px] h-[500px]";
  };

  return (
    <div className="w-full p-4 flex flex-col items-center">
      <div className="w-full max-w-4xl mb-4 flex sm:flex-row justify-between items-center gap-4">
        <div className="flex-col cloud-coverage-selector">
          <label className="font-semibold text-gray-500">
          Set Uniform Cloud Cover
          </label>
          <Select
            className="max-w-xs mt-2"
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
        </div>
        <div className="panel-orientation">
          <label className="font-semibold text-gray-500">
            Solar Panel Orientation
          </label>
          <RadioGroup
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
        className="border-double border-5 border-indigo-500 rounded-xl w-[80vw] h-[80vh] map-container"
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
        {markersData.map((marker) => (
          <Marker
            key={marker.id}
            position={marker.position}
            eventHandlers={{
              click: () => handleMarkerClick(marker.id),
            }}
          >
            <Popup
              className={`custom-popup-zoom-${Math.floor(zoomLevel)}`}
              maxWidth={800}
              minWidth={300}
            >
              {selectedMarkerData && (
                <div className={`${getPopupSize(zoomLevel)} bg-white p-4`}>
                  <h3 className="text-xl font-semibold text-center mb-4">
                    Energy Chart for {selectedMarkerData.label}
                  </h3>
                  <div className="w-full h-full">
                    <EnergyChart
                      path={selectedMarkerData.csvPath}
                      zoomLevel={zoomLevel}
                    />
                  </div>
                </div>
              )}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <Joyride
        steps={tourSteps}
        run={runTour}
        continuous={true}
        showSkipButton={true}
        showProgress={true}
        styles={{
          options: {
            primaryColor: '#4F46E5',
            backgroundColor: '#ffffff',
            textColor: '#333',
            zIndex: 9999,
          },
          tooltip: {
            position: 'relative',
            zIndex: 9999,
          },
          overlay: {
            position: 'fixed',
            zIndex: 9999,
          },
        }}
        floaterProps={{
          styles: {
            wrapper: {
              zIndex: 9999,
            },
          },
        }}
        callback={(data) => {
          const { status } = data;
          if (status === 'finished' || status === 'skipped') {
            setRunTour(false);
          }
        }}
      />
      <button
        onClick={() => setRunTour(true)}
        className="fixed bottom-4 right-4 bg-indigo-500 text-white px-4 py-2 rounded-lg shadow-md hover:bg-indigo-600 transition-colors"
      >
        Start Tour
      </button>
    </div>
  );
}
export default LeafletMap;
