import "./App.css";
import LeafletMap from "./Components/LeafletMap";
import "./styles/styles.css";
import { NextUIProvider } from "@nextui-org/react";
function App() {
  return (
    <NextUIProvider>
      <div className="bg-gradient-to-r from-lime-500 to-amber-500 min-h-screen">
        <div className="map-wrapper sm:container mx-auto">
          <LeafletMap />
        </div>
      </div>
    </NextUIProvider>
  );
}

export default App;
