from visclo.parser import parse


def test_one_node():
    definition = '''
        +-----------------+
        | my_vps: droplet |
        | foo: bar        |
        +-----------------+
    '''
    graph_elements = parse(definition)
    (node,), () = graph_elements
    assert node.attributes == dict(my_vps='droplet', foo='bar')


def test_two_nodes_and_an_edge():
    definition = '''
        +----------+
        | foo: bar |
        +----------+
             |
             v
        +--------------+
        | hello: world |
        +--------------+
    '''
    graph_elements = parse(definition)
    (node1, node2), (edge1,) = graph_elements
    assert node1.attributes == dict(foo='bar')
    assert node2.attributes == dict(hello='world')
    assert edge1.sources == (node1,)
    assert edge1.destinations == (node2,)


def test_droplet_behind_fw_with_storage():
    definition = '''
        +-----------------+  +------------------------+
        | my_vps: droplet |->| my_disk: block_storage |
        +-----------------+  +------------------------+
                 |
                 v
        +-----------------+
        | my_fw: firewall |
        +-----------------+
    '''
    graph_elements = parse(definition)
    nodes, edges = graph_elements
    node1, node2, node3 = nodes
    assert node1.attributes == dict(my_vps='droplet')
    assert node2.attributes == dict(my_disk='block_storage')
    assert node3.attributes == dict(my_fw='firewall')
    edge1, edge2 = edges
    assert edge1.sources == (node1,)
    assert edge1.destinations == (node2,)
    assert edge2.sources == (node1,)
    assert edge2.destinations == (node3,)
