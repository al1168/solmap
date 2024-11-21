import React, { useEffect, useState } from "react";
import Papa from "papaparse";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { useMap } from "react-leaflet";

interface DataPoint {
  week: string;
  energy_per_day: number;
  day_count: number;
  energy_per_day_std: number;
  energy_uncert_hi: number;
  energy_uncert_lo: number;
}
interface EnergyChartProps {
  path: string;
  zoomLevel: number;
}
const EnergyChart: React.FC<EnergyChartProps> = ({ path, zoomLevel }) => {
  const [chartData, setChartData] = useState<DataPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const map = useMap();
  useEffect(() => {
    console.log("Attempting to load CSV from:", path);

    Papa.parse(path, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        console.log("Successfully parsed CSV data:", results.data);
        if (results.data.length === 0) {
          setError("No data found in CSV file");
          return;
        }
        setChartData(results.data as DataPoint[]);
      },
      error: (error) => {
        console.error("Error parsing CSV:", error);
        setError(`Failed to parse CSV: ${error.message}`);
      },
    });
  }, [path]);

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  if (chartData.length === 0) {
    return <div>Loading chart data...</div>;
  }

  const getChartDimensions = (zoom: number) => {
    if (zoom <= 4) return { width: 350, height: 250 };
    if (zoom <= 5) return { width: 450, height: 300 };
    if (zoom <= 6) return { width: 550, height: 350 };
    if (zoom <= 7) return { width: 650, height: 400 };
    return { width: 750, height: 450 };
  };

  const dimensions = getChartDimensions(zoomLevel);

  return (
    <div>
      <h1>Energy Production Chart</h1>
      <LineChart
        width={dimensions.width}
        height={dimensions.height}
        data={chartData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="week" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="energy_per_day" stroke="#8884d8" />
        <Line type="monotone" dataKey="energy_uncert_hi" stroke="#82ca9d" />
        <Line type="monotone" dataKey="energy_uncert_lo" stroke="#ffc658" />
      </LineChart>
    </div>
  );
};

export default EnergyChart;
