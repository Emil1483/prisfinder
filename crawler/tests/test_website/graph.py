class Graph:
    def __init__(self):
        self.graph = {}

    @property
    def nodes(self) -> list[str]:
        return [*self.graph.keys()]

    def add_node(self, node):
        if node not in self.graph:
            self.graph[node] = []

    def add_edge(self, node1, node2, two_way=True):
        if node1 in self.graph and node2 in self.graph:
            if node2 not in self.graph[node1]:
                self.graph[node1].append(node2)
            if two_way:
                self.add_edge(node2, node1, two_way=False)

    def get_neighbors(self, node):
        if node in self.graph:
            return self.graph[node]
        else:
            return []

    def __str__(self):
        return str(self.graph)
