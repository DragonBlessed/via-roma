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
          
          setNetworkFeatureCount(
            networkData.feature_count ??
            networkData.features?.length ??
            0
          );

          console.log(
            "Transportation network loaded:",
            networkData.feature_count,
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
                data: networkData,
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


    originMarkerRef.current
      ?.remove();

    destinationMarkerRef.current
      ?.remove();


    originMarkerRef.current =
      null;

    destinationMarkerRef.current =
      null;


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


    map.addLayer({

      id:
        ROUTE_LAYER_ID,

      type:
        "line",

      source:
        ROUTE_SOURCE_ID,

      layout: {

        "line-join":
          "round",

        "line-cap":
          "round",

      },

      paint: {

        "line-color":
          "#b32323",

        "line-width":
          5,

        "line-opacity":
          0.9,

      },

    });


    originMarkerRef.current
      ?.remove();

    destinationMarkerRef.current
      ?.remove();


    originMarkerRef.current =
      new Marker({
        color:
          "#1d7a36",
      })

        .setLngLat([
          routeData.origin.longitude,
          routeData.origin.latitude,
        ])

        .addTo(map);


    destinationMarkerRef.current =
      new Marker({
        color:
          "#b32323",
      })

        .setLngLat([
          routeData
            .destination
            .longitude,

          routeData
            .destination
            .latitude,
        ])

        .addTo(map);


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
                <input
                  id="destination"
                  type="text"

                  value={
                    destinationQuery
                  }

                  placeholder="Search or choose a Roman place..."

                  autoComplete="off"

                  onFocus={() =>
                    setDestinationDropdownOpen(
                      true
                    )
                  }

                  onBlur={(event) => {

                    const nextFocus =
                      event.relatedTarget;

                    if (
                      !nextFocus ||
                      !event.currentTarget
                        .parentElement
                        ?.contains(
                          nextFocus as Node
                        )
                    ) {

                      setDestinationDropdownOpen(
                        false
                      );

                    }

                  }}

                  onChange={(event) =>
                    handleDestinationChange(
                      event.target.value
                    )
                  }
                />
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
                        Construction:
                      </strong>{" "}

                      {
                        selectedSegment
                          .construction_period
                      }
                    </p>
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