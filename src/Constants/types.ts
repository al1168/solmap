export interface FeatureCollection<T extends Geometry> {
    type: string;
    features: Feature<T>[]; // Array of features with generic geometry
}

export interface Feature<T extends Geometry> {
    type: string;
    properties: FeatureProperties;
    geometry: T;
}

export interface FeatureProperties {
    GEO_ID: string;
    STATE: string;
    CD: string;
    NAME: string;
    LSAD: string;
    CENSUSAREA: number;
    generation_real?: number; // Optional to support additional datasets
}

export interface Geometry {
    type: string;
}

export interface PointGeometry extends Geometry {
    type: "Point";
    coordinates: number[]; // [longitude, latitude]
}

export interface PolygonGeometry extends Geometry {
    type: "Polygon";
    coordinates: number[][][]; // Polygon coordinate structure: rings of coordinates
}

export interface MultiPolygonGeometry extends Geometry {
    type: "MultiPolygon";
    coordinates: number[][][][]; // MultiPolygon: Array of polygons, each with rings
}

// Specific types for your datasets
export type GenerationPoints = FeatureCollection<PointGeometry>;
export type StatesData = FeatureCollection<PolygonGeometry | MultiPolygonGeometry>;