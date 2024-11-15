import { FeatureCollection, FeatureProperties, PointGeometry, PolygonGeometry } from "../../Constants/types";
// Type guard to check if a key is valid for FeatureProperties
function isKeyOfFeatureProperties(key: string): key is keyof FeatureProperties {
    return ["GEO_ID", "STATE", "CD", "NAME", "LSAD", "CENSUSAREA", "generation_real"].includes(key);
}

export default function mergeGeoJSONByID(
    polygonGeoJSON: FeatureCollection<PolygonGeometry>,
    pointGeoJSON: FeatureCollection<PointGeometry>,
    idProperty = "GEO_ID"
): FeatureCollection<PolygonGeometry> {
    // Create a map for fast lookup of points by `GEO_ID`
    const pointMap = new Map<string, FeatureProperties>();

    // Populate the point map with points using `GEO_ID` as the key
    pointGeoJSON.features.forEach((pointFeature) => {
        if (isKeyOfFeatureProperties(idProperty)) {
            const geoID = pointFeature.properties[idProperty] as string; // Ensure geoID is a string
            if (geoID) {
                pointMap.set(geoID, pointFeature.properties);
            }
        }
    });

    // Loop over polygon features and merge with point data if the `GEO_ID` matches
    const mergedFeatures = polygonGeoJSON.features.map((polygonFeature) => {
        if (isKeyOfFeatureProperties(idProperty)) {
            const geoID = polygonFeature.properties[idProperty] as string; // Ensure geoID is a string
            const pointProperties = pointMap.get(geoID);

            // If a matching point is found, merge its properties into the polygon
            if (pointProperties) {
                polygonFeature.properties = {
                    ...polygonFeature.properties,
                    ...pointProperties, // Add point properties to polygon properties
                };
            }
        }

        return polygonFeature;
    });

    // Return a new GEOJSON object with merged features
    return {
        type: "FeatureCollection",
        features: mergedFeatures,
    };
}
