import heapq
import math


def dijkstra_shortest_path(
    graph,
    source,
    target,
    weight="distance_km",
):
    """
    Calculate a shortest path through a NetworkX
    MultiDiGraph using Dijkstra's algorithm.

    Returns:
        distance
        ordered node path
        ordered graph edges
    """

    if source not in graph:
        raise ValueError(
            f"Source node {source} not found."
        )

    if target not in graph:
        raise ValueError(
            f"Target node {target} not found."
        )


    distances = {
        source: 0.0
    }

    previous = {}

    queue = [
        (0.0, source)
    ]

    visited = set()


    while queue:

        current_distance, current = (
            heapq.heappop(queue)
        )


        if current in visited:
            continue


        visited.add(current)


        if current == target:
            break


        for neighbor, edges in (
            graph[current].items()
        ):

            for edge_key, attributes in (
                edges.items()
            ):

                edge_weight = attributes.get(
                    weight
                )

                if edge_weight is None:
                    continue


                edge_weight = float(
                    edge_weight
                )


                if edge_weight < 0:
                    raise ValueError(
                        "Dijkstra cannot process "
                        "negative weights."
                    )


                candidate = (
                    current_distance
                    + edge_weight
                )


                if candidate < distances.get(
                    neighbor,
                    math.inf,
                ):

                    distances[neighbor] = candidate

                    previous[neighbor] = (
                        current,
                        edge_key,
                    )


                    heapq.heappush(
                        queue,
                        (
                            candidate,
                            neighbor,
                        ),
                    )


    if target not in distances:

        raise ValueError(
            f"No route exists from "
            f"{source} to {target}."
        )


    # -----------------------------------------------------
    # Reconstruct path
    # -----------------------------------------------------

    edges = []

    current = target


    while current != source:

        previous_node, edge_key = (
            previous[current]
        )


        edges.append(
            (
                previous_node,
                current,
                edge_key,
            )
        )


        current = previous_node


    edges.reverse()


    nodes = [source]

    for _, destination, _ in edges:
        nodes.append(destination)


    return {
        "distance": distances[target],
        "nodes": nodes,
        "edges": edges,
    }