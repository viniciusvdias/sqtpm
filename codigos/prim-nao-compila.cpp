#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <limits>

sdsddusing namespace std;

// Define a type for the priority queue elements:
// (weight, vertex)
// The 'greater' comparator makes it a Min-Priority Queue based on weight.
using Edge = pair<int, int>;
using MinPriorityQueue = priority_queue<Edge, vector<Edge>, greater<Edge>>;

// Function to find the Minimum Spanning Tree (MST) weight using Prim's Algorithm
long long prim_mst(int num_vertices, const vector<vector<Edge>>& adj) {
    if (num_vertices == 0) {
        return 0;
    }

    // 1. Minimum weight to connect a vertex to the MST
    // Initialized to infinity (a large value)
    vector<int> min_weight(num_vertices + 1, numeric_limits<int>::max());

    // 2. Keep track of vertices already included in the MST
    vector<bool> in_mst(num_vertices + 1, false);

    // 3. Priority Queue (Min-Heap) to store edges to consider: (weight, vertex)
    // Start with vertex 1 (assuming 1-based indexing)
    MinPriorityQueue pq;

    // Start Prim's from an arbitrary vertex, typically vertex 1
    int start_node = 1;
    min_weight[start_node] = 0;
    // Push the starting edge (weight 0) into the priority queue
    pq.push({0, start_node});

    long long mst_weight = 0;
    int edges_in_mst = 0;

    while (!pq.empty() && edges_in_mst < num_vertices - 1) {
        // Get the edge with the minimum weight
        auto [weight, u] = pq.top();
        pq.pop();

        // Check if the vertex 'u' is already in the MST
        if (in_mst[u]) {
            continue;
        }

        // Include vertex 'u' into the MST
        in_mst[u] = true;
        mst_weight += weight;
        edges_in_mst++;

        // Explore neighbors of 'u'
        for (const auto& edge : adj[u]) {
            int v = edge.first;
            int edge_weight = edge.second;

            // If vertex 'v' is not in MST and the current edge weight
            // is smaller than the recorded minimum weight to reach 'v'
            if (!in_mst[v] && edge_weight < min_weight[v]) {
                min_weight[v] = edge_weight;
                pq.push({edge_weight, v});
            }
        }
    }

    // A check to see if all vertices were reachable (graph is connected)
    if (edges_in_mst == num_vertices - 1) {
        return mst_weight;
    } else {
        // If the graph is not connected, an MST does not exist for the whole graph
        // (This problem usually assumes a connected graph)
        return -1; // Or throw an error/return a special value
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N, M; // N: number of vertices, M: number of edges

    // Read N and M
    if (!(cin >> N >> M)) return 0;

    // Adjacency List: adj[u] stores pairs {v, weight} for edges (u, v)
    // Size N+1 for 1-based indexing
    vector<vector<Edge>> adj(N + 1);

    // Read M edges
    for (int i = 0; i < M; ++i) {
        int u, v, w; // u, v: vertices; w: weight
        if (!(cin >> u >> v >> w)) return 0;

        // Since the graph is undirected for MST, add edges both ways
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }

    // Calculate and print the MST weight
    long long result = prim_mst(N, adj);

    // Assuming the graph is connected and 1-based indexing is used
    cout << result << endl;

    return 0;
}
