import time
from queue import PriorityQueue


class Packet:
    def __init__(self, data, dest_addr, sender_addr, hop_limit, size, **kwargs):
        self.data = data
        self.dest_addr = dest_addr
        self.sender_addr = sender_addr
        self.hop_limit = hop_limit
        self.size = size
        self.other_info = kwargs


class Network:
    def __init__(self):
        """nodes of the form {address: RoutingNode instance}"""
        self.nodes = {}
        self.infinity = 100 ###

    def join_node(self, address, node):
        self.nodes[address] = node


class RoutingNode:
    ALIVE_TIMEOUT = 100


    def __init__(self, address, neighbors, network):
        """neighbors in the form {neighbor address: link cost}"""
        self.neighbors = neighbors
        self.address = address
        current_time = time.time()
        self.neighbors_last_hello = {neighbor: current_time for neighbor in neighbors.keys()}
        self.routing_table = {}  # {dest, next node address}

        self.network = network
        self.network.join_node(address, self)

    def adv(self):
        pass

    def send_adv(self):
        advertisement = self.adv()
        for neighbor in self.neighbors.keys():
            self.network.nodes[neighbor].rec_adv(advertisement)

    def integrate(self):
        pass

    def forward(self, packet):
        # TODO: check for infinity cost before forwarding
        if self.address == packet.dest_addr:
            print("Packet Arrived")
            # TODO: give packet to application?
            pass
        elif packet.hop_limit > 0:
            # process packet
            packet.hop_limit -= 1
            # TODO: put packet on queue, rather than just sending it to next node
            next_node = self.network.nodes[self.routing_table[packet.dest_addr]]
            next_node.forward(packet)
        else:
            # hop limit reached, drop the packet
            packet.destroy()

    def say_hello(self):
        for neighbor in self.neighbors.keys():
            self.network.nodes[neighbor].rec_hello(self, from_neighbor=self.address)

    def rec_hello(self, from_neighbor):
        self.neighbors_last_hello[from_neighbor] = time.time()


class DistanceVectorNode(RoutingNode):
    def __init__(self, address, neighbors, network):
        super(DistanceVectorNode, self).__init__(address, neighbors, network)

        # of the form {destination_node: (next node, cost to destination from that node + cost to that node from here)}
        self.path_costs = {}
        self.received_ads = []

    def adv(self):
        """returns an advertisement (self address, {destination_node: cost from here})
        only considers a path cost non-infinite if it passes through alive nodes"""

        alive_neighbors = set()
        for neighbor in self.neighbors.keys():
            if self.neighbors_last_hello[neighbor] < RoutingNode.ALIVE_TIMEOUT:
                alive_neighbors.add(neighbor)
            else:
                nodes = self.routing_table.keys()
                for node in nodes:
                    if self.routing_table[node] == neighbor:
                        self.routing_table[node] = None
                        self.path_costs[node] = self.network.infinity

        return self.address, {dest: cost for dest, next_node, cost in self.path_costs.items()}

    def integrate(self):
        """check each pending advertisement to see if a new route has a cheaper path than the current"""
        for neighbor, ad in self.received_ads:
            for a_dest, a_cost in ad.items():
                if (a_cost + self.neighbors[neighbor]) < self.path_costs[a_dest]:
                    self.path_costs[a_dest] = a_cost + self.neighbors[neighbor]
                    self.routing_table[a_dest] = neighbor
        self.received_ads = []

    def rec_adv(self, advertisement):
        assert(advertisement is not None)
        self.received_ads.append(advertisement)


class LinkStateNode(RoutingNode):

    def __init__(self, address, neighbors, network):
        super(LinkStateNode, self).__init__(address, neighbors, network)
        self.seq_num = -1

        self.received_ads = {}  # of the form {node address: (latest seq_num, {neighbor: cost to neighbor})

    def adv(self):
        """returns an advertisement (self address, seq_num, {neighbor: cost to neighbor})"""
        self.seq_num += 1
        # TODO could forget about ads sent after ever 5 seq_nums or so
        return self.address, self.seq_num, self.neighbors

    def rec_adv(self, advertisement):
        """if not done so already,
        adds the adv to the pending list to integrate, and passes on the adv to each neighbor"""
        assert(advertisement is not None)
        node_address = advertisement[0]
        seq = advertisement[1]

        # don't receive your own adv
        if node_address == self.address:
            return

        # update received_ads information to be the most recent from each node, and pass on the information once
        if node_address not in self.received_ads or self.received_ads[node_address][0] < seq:
            self.received_ads[node_address] = seq, advertisement[2]
            for neighbor in self.neighbors.keys():
                self.network.nodes[neighbor].rec_adv(advertisement)

    def integrate(self):
        """Run Djikstra's shortest path algorithm on the network, using the info in received_ads
        then set the routing table entries based on the shortest paths"""
        class Node:
            """Node object for shortest path finding"""

            def __init__(self, address, previous, cost):
                self.address = address
                self.previous = previous
                self.cost = cost

            def route_address(self):
                if self.previous is None:
                    return self.address
                return self.previous.route_address()

        addresses_found = set()
        nodes_found = []
        pq = PriorityQueue()
        # start the pq with nodes next to self
        root = Node(self.address, None, 0)
        for neighbor, link_cost in self.neighbors.items():
            pq.put(Node(neighbor, root, link_cost))

        while not pq.empty():
            this_node = pq.get()
            if this_node.address in addresses_found:
                # skip the node if we already found it by a cheaper path
                continue
            nodes_found.append(this_node)
            addresses_found.add(this_node.address)

            for seq, neighbor, link_cost in self.received_ads[this_node.address]:
                # consider each neighbor, unless a shortest path to it was already found
                if neighbor not in addresses_found:
                    pq.put(Node(neighbor, this_node, this_node.cost + link_cost))

        # Build the routing table from the shortest path information
        for node in nodes_found:
            self.routing_table[node.address] = node.route_address




