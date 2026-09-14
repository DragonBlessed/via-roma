import networkx as nx

from backend.routing.dijkstra import (
    dijkstra_shortest_path,
)


def test_shortest_path():

    graph = nx.MultiDiGraph()

    graph.add_edge(
        "A",
        "B",
        distance_km=5,
    )

    graph.add_edge(
        "A",
        "C",
        distance_km=9,
    )

    graph.add_edge(
        "B",
        "D",
        distance_km=2,
    )

    graph.add_edge(
        "C",
        "D",
        distance_km=1,
    )


    result = dijkstra_shortest_path(
        graph,
        "A",
        "D",
    )


    assert result["distance"] == 7

    assert result["nodes"] == [
        "A",
        "B",
        "D",
    ]