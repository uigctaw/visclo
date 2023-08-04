import sys

from visclo import parser
from visclo import digital_ocean


def create_droplet(api_token):
    agent = digital_ocean.Agent(api_token=api_token)
    nodes, edges = parser.parse('''
        +------------------+
        | name: my_droplet |
        | type: droplet    |
        +------------------+
    ''')
    agent.make_it_be(nodes=nodes, edges=edges)



if __name__ == '__main__':
    api_token = sys.argv[1]
    create_droplet(api_token)
