import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";

import workerUrl from
  "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

import "maplibre-gl/dist/maplibre-gl.css";
import "./App.css";
import * as maplibregl from "maplibre-gl";

import type {
  LineLayerSpecification,
} from "maplibre-gl";


setWorkerUrl(workerUrl);


const API_BASE_URL =
  "http://127.0.0.1:8000";

const ROUTE_SOURCE_ID =
  "via-roma-route";

const ROUTE_LAYER_ID =
  "via-roma-route-line";

const NETWORK_SOURCE_ID =
  "via-roma-network";

const NETWORK_LAYER_ID =
  "via-roma-network-lines";

const SELECTED_SEGMENT_SOURCE_ID =
  "via-roma-selected-segment";

const SELECTED_SEGMENT_LAYER_ID =
  "via-roma-selected-segment-line";

const SUGGESTED_PLACES_SOURCE_ID =
  "via-roma-suggested-places";

const SUGGESTED_PLACES_CIRCLE_LAYER_ID =
  "via-roma-suggested-place-circles";

const SUGGESTED_PLACES_LABEL_LAYER_ID =
  "via-roma-suggested-place-labels";

type HealthResponse = {
  status: string;

  graph: {
    nodes: number;
    edges: number;
    mapped_places: number;
    unique_place_nodes: number;
  };
};


type Place = {
  pleiades_id: number;
  name: string;
  graph_node_id: number;

  itinere_id:
  number | null;

  road_name:
  string | null;

  road_type:
  string | null;

  transport_mode:
  string | null;

  distance_to_network_km:
  number;

  longitude:
  number;

  latitude:
  number;
};

type SuggestedPlacesResponse = {
  count: number;
  results: Place[];
};

type PlaceSearchResponse = {
  query: string;
  count: number;
  results: Place[];
};


type RouteGeometry = {
  type: "LineString";
  coordinates: number[][];
};


type RouteSegment = {
  route_order: number;

  source_node: number;
  target_node: number;
  edge_key: number;

  itinere_id:
  number | null;

  road_name:
  string | null;

  road_type:
  string | null;

  transport_mode:
  string | null;

  distance_km:
  number;

  certainty:
  string | null;

  lower_date:
  number | string | null;

  upper_date:
  number | string | null;

  construction_period:
  string | null;

  coordinates:
  number[][];
};

type SelectedSegment = {
  source:
  "route" | "network";

  route_order:
  number | null;

  itinere_id:
  number | null;

  road_name:
  string | null;

  road_type:
  string | null;

  transport_mode:
  string | null;

  distance_km:
  number;

  certainty:
  string | null;

  lower_date:
  number | string | null;

  upper_date:
  number | string | null;

  construction_period:
  string | null;
};

function isUnknownChronologyDate(
  value: number | string | null | undefined
): boolean {

  if (
    value === null ||
    value === ""
  ) {
    return true;
  }

  const numericValue =
    Number(value);

  if (
    Number.isNaN(
      numericValue
    )
  ) {
    return false;
  }

  return (
    numericValue === 0 ||
    numericValue === 9999
  );
}


type ChronologyEvidenceLevel =
  | "explicit_range"
  | "partial_date"
  | "construction_attribution_only"
  | "none";


function chronologyEvidenceLevel(
  lowerDate:
    number | string | null | undefined,
  upperDate:
    number | string | null | undefined,
  constructionPeriod:
    string | null | undefined
): ChronologyEvidenceLevel {

  const hasLower =
    !isUnknownChronologyDate(
      lowerDate
    );

  const hasUpper =
    !isUnknownChronologyDate(
      upperDate
    );

  const hasConstruction =
    typeof constructionPeriod ===
      "string" &&
    constructionPeriod
      .trim()
      .length > 0;

  if (
    hasLower &&
    hasUpper
  ) {
    return "explicit_range";
  }

  if (
    hasLower ||
    hasUpper
  ) {
    return "partial_date";
  }

  if (hasConstruction) {
    return (
      "construction_attribution_only"
    );
  }

  return "none";
}


function chronologyEvidenceLabel(
  lowerDate:
    number | string | null | undefined,
  upperDate:
    number | string | null | undefined,
  constructionPeriod:
    string | null | undefined
): string {

  const level =
    chronologyEvidenceLevel(
      lowerDate,
      upperDate,
      constructionPeriod
    );

  if (
    level === "explicit_range"
  ) {
    return "Explicit date range";
  }

  if (
    level === "partial_date"
  ) {
    return "Partial explicit date evidence";
  }

  if (
    level ===
      "construction_attribution_only"
  ) {
    return "Construction attribution only";
  }

  return "No usable chronology";
}


function formatChronologyDate(
  value: number | string | null
): string {

  if (
    isUnknownChronologyDate(
      value
    )
  ) {
    return "Unknown";
  }

  const numericValue =
    Number(value);

  if (
    Number.isNaN(
      numericValue
    )
  ) {
    return String(value);
  }

  if (numericValue < 0) {
    return `${Math.abs(
      numericValue
    )} BCE`;
  }

  return `${numericValue} CE`;
}


function formatChronologyRange(
  lowerDate: number | string | null,
  upperDate: number | string | null
): string {

  const lowerUnknown =
    isUnknownChronologyDate(
      lowerDate
    );

  const upperUnknown =
    isUnknownChronologyDate(
      upperDate
    );

  if (
    lowerUnknown &&
    upperUnknown
  ) {
    return "Not available";
  }

  if (
    !lowerUnknown &&
    upperUnknown
  ) {
    return (
      `From ${formatChronologyDate(
        lowerDate
      )}; end date unknown`
    );
  }

  if (
    lowerUnknown &&
    !upperUnknown
  ) {
    return (
      `Start date unknown; through ${formatChronologyDate(
        upperDate
      )}`
    );
  }

  return (
    `${formatChronologyDate(
      lowerDate
    )} → ${formatChronologyDate(
      upperDate
    )}`
  );
}


type RouteResponse = {
  origin: Place;
  destination: Place;

  distance_km:
  number;

  segment_distance_km:
  number;

  node_count:
  number;

  edge_count:
  number;

  node_ids:
  number[];

  distance_by_mode_km:
  Record<string, number>;

  geometry:
  RouteGeometry;

  segments:
  RouteSegment[];
};


function App() {

  const mapContainer =
    useRef<HTMLDivElement | null>(
      null
    );

  const mapRef =
    useRef<MapLibreMap | null>(
      null
    );


  const originMarkerRef =
    useRef<Marker | null>(
      null
    );

  const destinationMarkerRef =
    useRef<Marker | null>(
      null
    );


  const [health, setHealth] =
    useState<HealthResponse | null>(
      null
    );

  const [apiError, setApiError] =
    useState<string | null>(
      null
    );


  const [originQuery, setOriginQuery] =
    useState("");

  const [
    destinationQuery,
    setDestinationQuery,
  ] = useState("");


  const [
    originResults,
    setOriginResults,
  ] = useState<Place[]>([]);

  const [
    destinationResults,
    setDestinationResults,
  ] = useState<Place[]>([]);

  const [
    suggestedPlaces,
    setSuggestedPlaces,
  ] = useState<Place[]>([]);

  const [
    originDropdownOpen,
    setOriginDropdownOpen,
  ] = useState(false);

  const [
    destinationDropdownOpen,
    setDestinationDropdownOpen,
  ] = useState(false);  

  const [
    selectedOrigin,
    setSelectedOrigin,
  ] = useState<Place | null>(
    null
  );

  const [
    selectedDestination,
    setSelectedDestination,
  ] = useState<Place | null>(
    null
  );


  const [
    route,
    setRoute,
  ] = useState<RouteResponse | null>(
    null
  );

  const [
    routeLoading,
    setRouteLoading,
  ] = useState(false);

  const [
    routeError,
    setRouteError,
  ] = useState<string | null>(
    null
  );

  const [
    networkVisible,
    setNetworkVisible,
  ] = useState(true);

  const [
    chronologyEvidenceVisible,
    setChronologyEvidenceVisible,
  ] = useState(false);

  const [
    selectedSegment,
    setSelectedSegment,
  ] = useState<SelectedSegment | null>(
    null
  );

  const [
  networkLoading,
  setNetworkLoading,
] = useState(true);

const [
  networkError,
  setNetworkError,
] = useState<string | null>(
  null
);

const [
  networkFeatureCount,
  setNetworkFeatureCount,
] = useState<number | null>(
  null
);

const [
  mapReady,
  setMapReady,
] = useState(false);


  // -------------------------------------------------------
  // Map initialization
  // -------------------------------------------------------

  useEffect(() => {

    if (
      !mapContainer.current ||
      mapRef.current
    ) {
      return;
    }


    const map =
      new MapLibreMap({

        container:
          mapContainer.current,

        style:
          "https://demotiles.maplibre.org/style.json",

        center: [
          16.0,
          38.0,
        ],

        zoom: 3.2,

      });


    map.addControl(
      new NavigationControl(),
      "top-right"
    );

    map.on(
      "load",
      async () => {
        setMapReady(
          true
        );

        setNetworkLoading(
          true
        );

        setNetworkError(
          null
        );
        try {
          const response =
            await fetch(
              `${API_BASE_URL}/network`
            );

          if (!response.ok) {
            throw new Error(
              `Network request failed: HTTP ${response.status
              }`
            );
          }

          const networkData =
            await response.json();

          const chronologyNetworkData = {
            ...networkData,

            features:
              (
                networkData.features ??
                []
              ).map(
                (feature: any) => {

                  const properties =
                    feature.properties ??
                    {};

                  return {
                    ...feature,

                    properties: {
                      ...properties,

                      chronology_evidence:
                        chronologyEvidenceLevel(
                          properties.lower_date,
                          properties.upper_date,
                          properties
                            .construction_period
                        ),
                    },
                  };
                }
              ),
          };

          setNetworkFeatureCount(
            chronologyNetworkData.feature_count ??
            chronologyNetworkData.features?.length ??
            0
          );

          console.log(
            "Transportation network loaded:",
            chronologyNetworkData.feature_count,
            "features"
          );

          if (
            !map.getSource(
              NETWORK_SOURCE_ID
            )
          ) {
            map.addSource(
              NETWORK_SOURCE_ID,
              {
                type: "geojson",
                data: chronologyNetworkData,
              }
            );
          }

          if (
            !map.getLayer(
              NETWORK_LAYER_ID
            )
          ) {
            const networkLayer:
              LineLayerSpecification = {
              id: NETWORK_LAYER_ID,

              type: "line" as const,

              source:
                NETWORK_SOURCE_ID,

              layout: {
                "line-join":
                  "round" as const,

                "line-cap":
                  "round" as const,
              },

              paint: {
                "line-color": [
                  "match",
                  [
                    "get",
                    "transport_mode",
                  ],

                  "sea",
                  "#3978a8",

                  "river",
                  "#4f8069",

                  "#866536",
                ],

                "line-width": [
                  "interpolate",
                  ["linear"],
                  ["zoom"],

                  4,
                  0.7,

                  7,
                  1.4,

                  10,
                  2.5,
                ],

                "line-opacity":
                  0.75,
              },
            };

            /*
            * If the calculated route already exists by the
            * time /network finishes loading, insert the
            * transportation network underneath it.
            */
            if (
              map.getLayer(
                ROUTE_LAYER_ID
              )
            ) {
              map.addLayer(
                networkLayer,
                ROUTE_LAYER_ID
              );
            }
            else {
              map.addLayer(
                networkLayer
              );
            }
          }
          const inspectSegment = (
            event: maplibregl.MapMouseEvent
          ) => {

            let feature = null;

            let source:
              "route" | "network" =
              "network";


            // Prefer the calculated route when it
            // overlaps the background network.
            if (
              map.getLayer(
                ROUTE_LAYER_ID
              )
            ) {

              const routeFeatures =
                map.queryRenderedFeatures(
                  event.point,
                  {
                    layers: [
                      ROUTE_LAYER_ID,
                    ],
                  }
                );


              if (
                routeFeatures.length > 0
              ) {

                feature =
                  routeFeatures[0];

                source =
                  "route";

              }

            }


            if (
              !feature &&
              map.getLayer(
                NETWORK_LAYER_ID
              )
            ) {

              const networkFeatures =
                map.queryRenderedFeatures(
                  event.point,
                  {
                    layers: [
                      NETWORK_LAYER_ID,
                    ],
                  }
                );


              if (
                networkFeatures.length > 0
              ) {

                feature =
                  networkFeatures[0];

                source =
                  "network";

              }

            }


            if (!feature) {

              setSelectedSegment(
                null
              );

              return;

            }


            const properties =
              feature.properties ?? {};


            setSelectedSegment({
              source,

              route_order:
                source === "route" &&
                  properties.route_order != null
                  ? Number(
                    properties.route_order
                  )
                  : null,

              itinere_id:
                properties.itinere_id != null
                  ? Number(
                    properties.itinere_id
                  )
                  : null,

              road_name:
                properties.road_name ??
                null,

              road_type:
                properties.road_type ??
                null,

              transport_mode:
                properties.transport_mode ??
                null,

              distance_km:
                Number(
                  properties.distance_km ??
                  0
                ),

              certainty:
                properties.certainty ??
                null,

              lower_date:
                properties.lower_date ??
                null,

              upper_date:
                properties.upper_date ??
                null,

              construction_period:
                properties
                  .construction_period ??
                null,
            });


            const highlightFeature = {
              type:
                "Feature" as const,

              properties: {},

              geometry:
                feature.geometry,
            };


            const existingSource =
              map.getSource(
                SELECTED_SEGMENT_SOURCE_ID
              );


            if (existingSource) {

              (
                existingSource as
                maplibregl.GeoJSONSource
              ).setData(
                highlightFeature
              );

            }
            else {

              map.addSource(
                SELECTED_SEGMENT_SOURCE_ID,
                {
                  type:
                    "geojson",

                  data:
                    highlightFeature,
                }
              );


              map.addLayer(
                {
                  id:
                    SELECTED_SEGMENT_LAYER_ID,

                  type:
                    "line",

                  source:
                    SELECTED_SEGMENT_SOURCE_ID,

                  layout: {
                    "line-join":
                      "round",

                    "line-cap":
                      "round",
                  },

                  paint: {
                    "line-color":
                      "#f4c542",

                    "line-width":
                      7,

                    "line-opacity":
                      1,
                  },
                }
              );

            }

          };


          map.on(
            "click",
            inspectSegment
          );


          map.on(
            "mousemove",
            (event) => {

              let interactive =
                false;


              if (
                map.getLayer(
                  ROUTE_LAYER_ID
                )
              ) {

                interactive =
                  map.queryRenderedFeatures(
                    event.point,
                    {
                      layers: [
                        ROUTE_LAYER_ID,
                      ],
                    }
                  ).length > 0;

              }


              if (
                !interactive &&
                map.getLayer(
                  NETWORK_LAYER_ID
                )
              ) {

                interactive =
                  map.queryRenderedFeatures(
                    event.point,
                    {
                      layers: [
                        NETWORK_LAYER_ID,
                      ],
                    }
                  ).length > 0;

              }


              map.getCanvas().style.cursor =
                interactive
                  ? "pointer"
                  : "";

            }
          );
        }
        catch (error) {

          console.error(
            "Transportation network failed to load:",
            error
          );

          setNetworkError(
            error instanceof Error
              ? error.message
              : "Transportation network failed to load."
          );

        }
        finally {

          setNetworkLoading(
            false
          );

        }
      }
    );

    mapRef.current = map;


    mapRef.current =
      map;


    return () => {

      originMarkerRef.current
        ?.remove();

      destinationMarkerRef.current
        ?.remove();

      setMapReady(
        false
      );

      map.remove();

      mapRef.current =
        null;

    };

  }, []);


  // -------------------------------------------------------
  // Backend health check
  // -------------------------------------------------------

  useEffect(() => {

    async function checkBackend() {

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/health`
          );


        if (!response.ok) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        const data:
          HealthResponse =
          await response.json();


        setHealth(data);

      }
      catch (error) {

        setApiError(

          error instanceof Error

            ? error.message

            : "Unknown API error"

        );

      }

    }


    checkBackend();

  }, []);


  useEffect(() => {

    async function loadSuggestedPlaces() {

      try {

        const response =
          await fetch(
            `${API_BASE_URL}/places/suggestions?limit=8`
          );

        if (!response.ok) {

          throw new Error(
            `Suggested places failed: HTTP ${response.status}`
          );

        }

        const data:
          SuggestedPlacesResponse =
          await response.json();

        setSuggestedPlaces(
          data.results
        );

      }
      catch (error) {

        console.error(
          "Suggested places failed to load:",
          error
        );

      }

    }

    loadSuggestedPlaces();

  }, []);


  // -------------------------------------------------------
  // Suggested places map layer
  // -------------------------------------------------------

  useEffect(() => {

    const map =
      mapRef.current;


    if (
      !map ||
      !mapReady
    ) {

      return;

    }


    const placeData = {
      type:
        "FeatureCollection" as const,

      features:
        suggestedPlaces.map(
          (place) => ({
            type:
              "Feature" as const,

            properties: {
              name:
                place.name,

              pleiades_id:
                place.pleiades_id,
            },

            geometry: {
              type:
                "Point" as const,

              coordinates: [
                place.longitude,
                place.latitude,
              ],
            },
          })
        ),
    };


    const existingSource =
      map.getSource(
        SUGGESTED_PLACES_SOURCE_ID
      );


    if (existingSource) {

      (
        existingSource as
          maplibregl.GeoJSONSource
      ).setData(
        placeData
      );

      return;

    }


    map.addSource(
      SUGGESTED_PLACES_SOURCE_ID,
      {
        type:
          "geojson",

        data:
          placeData,
      }
    );


    map.addLayer({
      id:
        SUGGESTED_PLACES_CIRCLE_LAYER_ID,

      type:
        "circle",

      source:
        SUGGESTED_PLACES_SOURCE_ID,

      paint: {

        "circle-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],

          3,
          5,

          6,
          8,

          9,
          11,
        ],

        "circle-color":
          "#000000",

        "circle-stroke-color":
          "#f5e6c8",

        "circle-stroke-width":
          2,

        "circle-opacity":
          0.95,
      },
    });


    map.addLayer({
      id:
        SUGGESTED_PLACES_LABEL_LAYER_ID,

      type:
        "symbol",

      source:
        SUGGESTED_PLACES_SOURCE_ID,

      layout: {

        "text-field": [
          "get",
          "name",
        ],

        "text-size": [
          "interpolate",
          ["linear"],
          ["zoom"],

          3,
          12,

          6,
          14,

          9,
          17,
        ],

        "text-offset": [
          0,
          1.15,
        ],

        "text-anchor":
          "top",

        "text-allow-overlap":
          false,

        "text-padding":
          3,
      },

      paint: {

        "text-color":
          "#2b2118",

        "text-halo-color":
          "#f5e6c8",

        "text-halo-width":
          1.5,
      },
    });

  }, [
    suggestedPlaces,
    mapReady,
  ]);


  // -------------------------------------------------------
  // Search helper
  // -------------------------------------------------------

  async function searchPlaces(
    query: string
  ): Promise<Place[]> {

    const trimmed =
      query.trim();


    if (
      trimmed.length < 2
    ) {

      return [];

    }


    const response =
      await fetch(

        `${API_BASE_URL}/places?query=${encodeURIComponent(
          trimmed
        )
        }&limit=8`

      );


    if (!response.ok) {

      throw new Error(

        `Place search failed: HTTP ${response.status
        }`

      );

    }


    const data:
      PlaceSearchResponse =
      await response.json();


    return data.results;

  }

  // -------------------------------------------------------
  // Origin search
  // -------------------------------------------------------

  useEffect(() => {

    if (!originDropdownOpen) {
      return;
    }


    const trimmed =
      originQuery.trim();


    // Empty field, or clicking an already-selected field:
    // show helpful starting places.
    if (
      trimmed.length === 0 ||
      (
        selectedOrigin &&
        originQuery === selectedOrigin.name
      )
    ) {

      setOriginResults(
        suggestedPlaces
      );

      return;

    }


    if (trimmed.length < 2) {

      setOriginResults([]);

      return;

    }


    const timeout =
      window.setTimeout(

        async () => {

          try {

            const results =
              await searchPlaces(
                originQuery
              );

            setOriginResults(
              results
            );

          }
          catch (error) {

            console.error(
              "Origin search failed:",
              error
            );

          }

        },

        250
      );


    return () => {

      window.clearTimeout(
        timeout
      );

    };

  }, [
    originQuery,
    originDropdownOpen,
    selectedOrigin,
    suggestedPlaces,
  ]);


  // -------------------------------------------------------
  // Destination search
  // -------------------------------------------------------

  useEffect(() => {

    if (!destinationDropdownOpen) {
      return;
    }


    const trimmed =
      destinationQuery.trim();


    if (
      trimmed.length === 0 ||
      (
        selectedDestination &&
        destinationQuery ===
          selectedDestination.name
      )
    ) {

      setDestinationResults(
        suggestedPlaces
      );

      return;

    }


    if (trimmed.length < 2) {

      setDestinationResults([]);

      return;

    }


    const timeout =
      window.setTimeout(

        async () => {

          try {

            const results =
              await searchPlaces(
                destinationQuery
              );

            setDestinationResults(
              results
            );

          }
          catch (error) {

            console.error(
              "Destination search failed:",
              error
            );

          }

        },

        250
      );


    return () => {

      window.clearTimeout(
        timeout
      );

    };

  }, [
    destinationQuery,
    destinationDropdownOpen,
    selectedDestination,
    suggestedPlaces,
  ]);


  // -------------------------------------------------------
  // Place selection
  // -------------------------------------------------------

  function chooseOrigin(
    place: Place
  ) {

    setSelectedOrigin(
      place
    );

    setOriginQuery(
      place.name
    );

    setOriginResults([]);

    setOriginDropdownOpen(
      false
    );

    clearRoute();

  }


  function chooseDestination(
    place: Place
  ) {

    setSelectedDestination(
      place
    );

    setDestinationQuery(
      place.name
    );

    setDestinationResults([]);

    setDestinationDropdownOpen(
      false
    );

    clearRoute();

  }


  function handleOriginChange(
    value: string
  ) {

    setOriginQuery(
      value
    );

    setSelectedOrigin(
      null
    );

    setOriginDropdownOpen(
      true
    );

    clearRoute();

  }


  function handleDestinationChange(
    value: string
  ) {

    setDestinationQuery(
      value
    );

    setSelectedDestination(
      null
    );

    setDestinationDropdownOpen(
      true
    );

    clearRoute();

  }

  // -------------------------------------------------------
  // Selected place markers
  // -------------------------------------------------------

  useEffect(() => {

    const map =
      mapRef.current;


    if (
      !map ||
      !mapReady
    ) {

      return;

    }


    originMarkerRef.current
      ?.remove();

    originMarkerRef.current =
      null;


    if (!selectedOrigin) {

      return;

    }


    const element =
      document.createElement(
        "div"
      );

    element.style.width =
      "18px";

    element.style.height =
      "18px";

    element.style.borderRadius =
      "50%";

    element.style.background =
      "#1d7a36";

    element.style.border =
      "3px solid #ffffff";

    element.style.boxShadow =
      "0 1px 5px rgba(0, 0, 0, 0.45)";


    originMarkerRef.current =
      new Marker({
        element,
        anchor:
          "center",
      })

        .setLngLat([
          selectedOrigin.longitude,
          selectedOrigin.latitude,
        ])

        .addTo(map);

  }, [
    selectedOrigin,
    mapReady,
  ]);


  useEffect(() => {

    const map =
      mapRef.current;


    if (
      !map ||
      !mapReady
    ) {

      return;

    }


    destinationMarkerRef.current
      ?.remove();

    destinationMarkerRef.current =
      null;


    if (!selectedDestination) {

      return;

    }


    const element =
      document.createElement(
        "div"
      );

    element.style.width =
      "18px";

    element.style.height =
      "18px";

    element.style.borderRadius =
      "50%";

    element.style.background =
      "#b32323";

    element.style.border =
      "3px solid #ffffff";

    element.style.boxShadow =
      "0 1px 5px rgba(0, 0, 0, 0.45)";


    destinationMarkerRef.current =
      new Marker({
        element,
        anchor:
          "center",
      })

        .setLngLat([
          selectedDestination.longitude,
          selectedDestination.latitude,
        ])

        .addTo(map);

  }, [
    selectedDestination,
    mapReady,
  ]);


  function kmToMiles(
    kilometers: number
  ) {
    return kilometers * 0.621371;
  }

  // -------------------------------------------------------
  // Clear existing map route
  // -------------------------------------------------------

  function clearRoute() {

    setRoute(null);

    setRouteError(null);

    setSelectedSegment(null);


    const map =
      mapRef.current;


    if (!map) {

      return;

    }


    if (
      map.getLayer(
        ROUTE_LAYER_ID
      )
    ) {

      map.removeLayer(
        ROUTE_LAYER_ID
      );

    }


    if (
      map.getSource(
        ROUTE_SOURCE_ID
      )
    ) {

      map.removeSource(
        ROUTE_SOURCE_ID
      );

    }

    if (
      map.getLayer(
        SELECTED_SEGMENT_LAYER_ID
      )
    ) {
      map.removeLayer(
        SELECTED_SEGMENT_LAYER_ID
      );
    }

    if (
      map.getSource(
        SELECTED_SEGMENT_SOURCE_ID
      )
    ) {
      map.removeSource(
        SELECTED_SEGMENT_SOURCE_ID
      );
    }
  }


  // -------------------------------------------------------
  // Draw route
  // -------------------------------------------------------

  function drawRoute(
    routeData: RouteResponse
  ) {

    const map =
      mapRef.current;


    if (!map) {

      return;

    }


    if (
      map.getLayer(
        ROUTE_LAYER_ID
      )
    ) {

      map.removeLayer(
        ROUTE_LAYER_ID
      );

    }


    if (
      map.getSource(
        ROUTE_SOURCE_ID
      )
    ) {

      map.removeSource(
        ROUTE_SOURCE_ID
      );

    }


    const routeFeatureCollection = {
      type:
        "FeatureCollection" as const,

      features:
        routeData.segments.map(
          (segment) => ({
            type:
              "Feature" as const,

            properties: {
              route_order:
                segment.route_order,

              itinere_id:
                segment.itinere_id,

              road_name:
                segment.road_name,

              road_type:
                segment.road_type,

              transport_mode:
                segment.transport_mode,

              distance_km:
                segment.distance_km,

              certainty:
                segment.certainty,

              lower_date:
                segment.lower_date,

              upper_date:
                segment.upper_date,

              construction_period:
                segment.construction_period,
            },

            geometry: {
              type:
                "LineString" as const,

              coordinates:
                segment.coordinates,
            },
          })
        ),
    };


    map.addSource(
      ROUTE_SOURCE_ID,
      {
        type: "geojson",
        data:
          routeFeatureCollection,
      }
    );


    const routeLayer:
      LineLayerSpecification = {

      id:
        ROUTE_LAYER_ID,

      type:
        "line" as const,

      source:
        ROUTE_SOURCE_ID,

      layout: {

        "line-join":
          "round" as const,

        "line-cap":
          "round" as const,

      },

      paint: {

        "line-color": [
          "match",
          [
            "get",
            "transport_mode",
          ],

          "road",
          "#b32323",

          "sea",
          "#3978a8",

          "river",
          "#4f8069",

          "transfer",
          "#f4c542",

          "#b32323",
        ],

        "line-width":
          5,

        "line-opacity":
          0.9,

      },

    };


    if (
      map.getLayer(
        SUGGESTED_PLACES_CIRCLE_LAYER_ID
      )
    ) {

      map.addLayer(
        routeLayer,
        SUGGESTED_PLACES_CIRCLE_LAYER_ID
      );

    }
    else {

      map.addLayer(
        routeLayer
      );

    }

    const coordinates =
      routeData
        .geometry
        .coordinates;


    if (
      coordinates.length > 0
    ) {

      const first =
        coordinates[0];


      const bounds =
        new LngLatBounds(

          [
            first[0],
            first[1],
          ],

          [
            first[0],
            first[1],
          ]

        );


      for (
        const coordinate
        of coordinates
      ) {

        bounds.extend([
          coordinate[0],
          coordinate[1],
        ]);

      }


      map.fitBounds(
        bounds,
        {
          padding: 80,
          duration: 1000,
        }
      );

    }

  }


  // -------------------------------------------------------
  // Route calculation
  // -------------------------------------------------------

  async function calculateRoute() {

    if (
      !selectedOrigin ||
      !selectedDestination
    ) {

      return;

    }

    clearRoute();


    setRouteLoading(
      true
    );

    setRouteError(
      null
    );


    try {

      const response =
        await fetch(

          `${API_BASE_URL}/route?origin=${selectedOrigin
            .pleiades_id
          }&destination=${selectedDestination
            .pleiades_id
          }`

        );


      if (!response.ok) {

        let message =
          `Route request failed: HTTP ${response.status
          }`;


        try {

          const errorData =
            await response.json();


          if (
            errorData.detail
          ) {

            message =
              String(
                errorData.detail
              );

          }

        }
        catch {

          // Keep default message.

        }


        throw new Error(
          message
        );

      }


      const routeData:
        RouteResponse =
        await response.json();


      setRoute(
        routeData
      );


      drawRoute(
        routeData
      );

    }
    catch (error) {

      setRouteError(

        error instanceof Error

          ? error.message

          : "Unable to calculate route."

      );

    }
    finally {

      setRouteLoading(
        false
      );

    }

  }

  function toggleNetwork() {
    const nextVisible =
      !networkVisible;

    setNetworkVisible(
      nextVisible
    );

    const map =
      mapRef.current;

    if (
      !map ||
      !map.getLayer(
        NETWORK_LAYER_ID
      )
    ) {
      return;
    }

    map.setLayoutProperty(
      NETWORK_LAYER_ID,
      "visibility",
      nextVisible
        ? "visible"
        : "none"
    );
  }


  function toggleChronologyEvidence() {
    const nextVisible =
      !chronologyEvidenceVisible;

    setChronologyEvidenceVisible(
      nextVisible
    );

    const map =
      mapRef.current;

    if (
      !map ||
      !map.getLayer(
        NETWORK_LAYER_ID
      )
    ) {
      return;
    }

    map.setPaintProperty(
      NETWORK_LAYER_ID,
      "line-color",
      nextVisible
        ? [
          "match",
          [
            "get",
            "chronology_evidence",
          ],

          "explicit_range",
          "#2f6f44",

          "partial_date",
          "#b7791f",

          "construction_attribution_only",
          "#6b5b95",

          "#9a9a9a",
        ]
        : [
          "match",
          [
            "get",
            "transport_mode",
          ],

          "sea",
          "#3978a8",

          "river",
          "#4f8069",

          "#866536",
        ]
    );

    map.setPaintProperty(
      NETWORK_LAYER_ID,
      "line-opacity",
      nextVisible
        ? 0.9
        : 0.75
    );
  }


  return (

    <div className="app">


      <aside className="sidebar">


        <h1>
          Via Roma
        </h1>


        <p className="subtitle">
          Roman Transportation
          Network Explorer
        </p>


        <section className="route-panel">


          <h2>
            Route Planner
          </h2>

          <label className="network-toggle">

            <input
              type="checkbox"
              checked={
                networkVisible
              }
              onChange={
                toggleNetwork
              }
            />

            <span>
              Show transportation network
            </span>

          </label>

          <label className="network-toggle">

            <input
              type="checkbox"
              checked={
                chronologyEvidenceVisible
              }
              disabled={
                networkLoading ||
                Boolean(networkError)
              }
              onChange={
                toggleChronologyEvidence
              }
            />

            <span>
              Color network by chronology evidence
            </span>

          </label>

          {
            chronologyEvidenceVisible &&
            (
              <div
                className="network-status"
                style={{
                  display: "grid",
                  gap: "4px",
                  marginTop: "6px",
                }}
              >
                <strong>
                  Chronology evidence
                </strong>

                <span>
                  ● Explicit date range
                </span>

                <span>
                  ◐ Partial explicit date evidence
                </span>

                <span>
                  ◆ Construction attribution only
                </span>

                <span>
                  ○ No usable chronology
                </span>
              </div>
            )
          }

          {
            networkLoading &&
            (
              <div className="network-status">
                Loading transportation network...
              </div>
            )
          }

          {
            !networkLoading &&
            networkFeatureCount !== null &&
            (
              <div className="network-status">
                Network loaded:{" "}
                {networkFeatureCount.toLocaleString()}
                {" "}segments
              </div>
            )
          }

          {
            networkError &&
            (
              <div className="network-status network-status-error">
                {networkError}
              </div>
            )
          }


          <div className="search-field">


            <label htmlFor="origin">
              Origin
            </label>


            <input

              id="origin"

              type="text"

              value={
                originQuery
              }

              placeholder="Search historical place..."

              autoComplete="off"

              onChange={(event) =>
                handleOriginChange(
                  event.target.value
                )
              }

            />


            {
              originDropdownOpen &&
              originResults.length > 0 &&
              (
                <div className="search-results">
                  {
                    (
                      originQuery.trim().length === 0 ||
                      (
                        selectedOrigin &&
                        originQuery === selectedOrigin.name
                      )
                    ) &&
                    (
                      <div className="search-results-heading">
                        Suggested Roman places
                      </div>
                    )
                  }
                  {
                    originResults.map(
                      (place) => (

                        <button

                          type="button"

                          className="search-result"

                          key={
                            place.pleiades_id
                          }

                          onClick={() =>
                            chooseOrigin(
                              place
                            )
                          }

                        >

                          <span className="place-name">

                            {
                              place.name
                            }

                          </span>


                          <span className="place-id">

                            Pleiades{" "}

                            {
                              place
                                .pleiades_id
                            }

                          </span>

                        </button>

                      )
                    )
                  }

                </div>
              )
            }


          </div>


          <div className="search-field">


            <label htmlFor="destination">
              Destination
            </label>


            <input

              id="destination"

              type="text"

              value={
                destinationQuery
              }

              placeholder="Search historical place..."

              autoComplete="off"

              onChange={(event) =>
                handleDestinationChange(
                  event.target.value
                )
              }

            />


            {
              destinationDropdownOpen &&
              destinationResults.length > 0 &&
              (
                <div className="search-results">
                  {
                    (
                      destinationQuery.trim().length === 0 ||
                      (
                        selectedDestination &&
                        destinationQuery ===
                          selectedDestination.name
                      )
                    ) &&
                    (
                      <div className="search-results-heading">
                        Suggested Roman places
                      </div>
                    )
                  }
                  {
                    destinationResults.map(
                      (place) => (

                        <button

                          type="button"

                          className="search-result"

                          key={
                            place.pleiades_id
                          }

                          onClick={() =>
                            chooseDestination(
                              place
                            )
                          }

                        >

                          <span className="place-name">

                            {
                              place.name
                            }

                          </span>


                          <span className="place-id">

                            Pleiades{" "}

                            {
                              place
                                .pleiades_id
                            }

                          </span>

                        </button>

                      )
                    )
                  }

                </div>
              )
            }


          </div>


          {
            selectedOrigin &&
            selectedDestination &&
            (
              <div className="selection-summary">


                <strong>
                  Route selected
                </strong>


                <p>

                  {
                    selectedOrigin.name
                  }

                  {" → "}

                  {
                    selectedDestination
                      .name
                  }

                </p>


                <small>

                  {
                    selectedOrigin
                      .pleiades_id
                  }

                  {" → "}

                  {
                    selectedDestination
                      .pleiades_id
                  }

                </small>


                <button

                  className="route-button"

                  type="button"

                  disabled={
                    routeLoading
                  }

                  onClick={
                    calculateRoute
                  }

                >

                  {
                    routeLoading

                      ? "Calculating..."

                      : "Calculate Route"
                  }

                </button>


              </div>
            )
          }


          {
            routeError &&
            (
              <div className="route-error">

                {
                  routeError
                }

              </div>
            )
          }


          {
            route &&
            (
              <div className="route-summary">


                <h3>
                  Route Result
                </h3>


                <p className="route-title">

                  {
                    route.origin.name
                  }

                  {" → "}

                  {
                    route
                      .destination
                      .name
                  }

                </p>


                <p>

                  <strong>
                    Distance:
                  </strong>{" "}

                  {
                    route
                      .distance_km
                      .toFixed(2)
                  }{" "}

                  km /{" "}
                  {
                    kmToMiles(
                      route.distance_km
                    ).toFixed(2)
                  }{" "}
                  mi

                </p>


                <p>

                  <strong>
                    Nodes:
                  </strong>{" "}

                  {
                    route.node_count
                  }

                </p>


                <p>

                  <strong>
                    Segments:
                  </strong>{" "}

                  {
                    route.edge_count
                  }

                </p>


                {
                  Object.entries(
                    route
                      .distance_by_mode_km
                  ).map(
                    ([
                      mode,
                      distance,
                    ]) => (

                      <p key={mode}>

                        <strong>
                          {
                            mode
                          }:
                        </strong>{" "}

                        {
                          distance
                            .toFixed(2)
                        }{" "}

                        km /{" "}
                        {
                          kmToMiles(
                            distance
                          ).toFixed(2)
                        }{" "}
                        mi

                      </p>

                    )
                  )
                }


              </div>
            )
          }

          {
            selectedSegment &&
            (
              <div className="segment-details">

                <h3>
                  Segment Details
                </h3>


                <p className="segment-source">

                  {
                    selectedSegment.source ===
                      "route"
                      ? "Calculated route"
                      : "Transportation network"
                  }

                </p>


                {
                  selectedSegment.road_name &&
                  (
                    <p>
                      <strong>
                        Name:
                      </strong>{" "}

                      {
                        selectedSegment
                          .road_name
                      }
                    </p>
                  )
                }


                {
                  selectedSegment.itinere_id !=
                  null &&
                  (
                    <p>
                      <strong>
                        Itiner-e ID:
                      </strong>{" "}

                      {
                        selectedSegment
                          .itinere_id
                      }
                    </p>
                  )
                }


                {
                  selectedSegment.road_type &&
                  (
                    <p>
                      <strong>
                        Type:
                      </strong>{" "}

                      {
                        selectedSegment
                          .road_type
                      }
                    </p>
                  )
                }


                {
                  selectedSegment
                    .transport_mode &&
                  (
                    <p>
                      <strong>
                        Mode:
                      </strong>{" "}

                      {
                        selectedSegment
                          .transport_mode
                      }
                    </p>
                  )
                }


                <p>
                  <strong>
                    Segment distance:
                  </strong>{" "}

                  {
                    selectedSegment
                      .distance_km
                      .toFixed(2)
                  }{" "}

                  km /{" "}
                  {
                    kmToMiles(
                      selectedSegment.distance_km
                    ).toFixed(2)
                  }{" "}
                  mi
                </p>


                {
                  selectedSegment.route_order !=
                  null &&
                  (
                    <p>
                      <strong>
                        Route segment:
                      </strong>{" "}

                      {
                        selectedSegment
                          .route_order
                      }
                    </p>
                  )
                }


                {
                  selectedSegment.certainty &&
                  (
                    <p>
                      <strong>
                        Certainty:
                      </strong>{" "}

                      {
                        selectedSegment
                          .certainty
                      }
                    </p>
                  )
                }


                {
                  selectedSegment
                    .construction_period &&
                  (
                    <p>
                      <strong>
                        Construction attribution:
                      </strong>{" "}

                      {
                        selectedSegment
                          .construction_period
                      }
                    </p>
                  )
                }


                {
                  selectedSegment.itinere_id !=
                  null &&
                  (
                    <div className="chronology-details">

                      <p>
                        <strong>
                          Source chronology:
                        </strong>{" "}

                        {
                          formatChronologyRange(
                            selectedSegment.lower_date,
                            selectedSegment.upper_date
                          )
                        }
                      </p>

                      <p>
                        <strong>
                          Chronology evidence:
                        </strong>{" "}

                        {
                          chronologyEvidenceLabel(
                            selectedSegment.lower_date,
                            selectedSegment.upper_date,
                            selectedSegment
                              .construction_period
                          )
                        }
                      </p>

                      <p className="chronology-note">
                        <small>
                          Itiner-e chronology is shown as
                          source evidence and does not
                          represent the complete operational
                          lifespan of this route. Raw 0 and
                          9999 date values are displayed as
                          unknown rather than literal years.
                        </small>
                      </p>

                    </div>
                  )
                }

              </div>
            )
          }

        </section>


        <section className="status-panel">


          <h2>
            Backend
          </h2>


          {
            health &&
            (
              <>

                <p className="online">

                  API connected

                </p>


                <p>

                  Nodes:{" "}

                  {
                    health
                      .graph
                      .nodes
                      .toLocaleString()
                  }

                </p>


                <p>

                  Edges:{" "}

                  {
                    health
                      .graph
                      .edges
                      .toLocaleString()
                  }

                </p>


                <p>

                  Mapped places:{" "}

                  {
                    health
                      .graph
                      .mapped_places
                      .toLocaleString()
                  }

                </p>

              </>
            )
          }


          {
            apiError &&
            (
              <p className="offline">

                API connection failed:{" "}

                {
                  apiError
                }

              </p>
            )
          }


          {
            !health &&
            !apiError &&
            (
              <p>
                Connecting...
              </p>
            )
          }


        </section>


      </aside>


      <main

        ref={
          mapContainer
        }

        className="map"

      />


    </div>

  );

}


export default App;