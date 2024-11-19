import "./App.css";
import LeafletMap from "./Components/LeafletMap";

import { NextUIProvider } from "@nextui-org/react";
function App() {
  return (
    <NextUIProvider>
      <div className="map-wrapper container mx-auto">
        <LeafletMap />
      </div>
    </NextUIProvider>
  );
}

export default App;
