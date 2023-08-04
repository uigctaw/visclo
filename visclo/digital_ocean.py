import urllib


class API:

    def __init__(self, token):
        self._token = token

    def get_droplets(self):
        pass

    def _https_get(self):
        pass



class Droplet:

    def __init__(self, node):
        self.name = node.attributes['name']


class Agent:

    def __init__(self, api_token):
        self._api = API(api_token)

    def make_it_be(self,*, nodes, edges):
        assert not edges
        node, = nodes
        assert node.attributes['type'] == 'droplet'
        required_droplet = Droplet(node)

        api = self._api
        existing_droplets = api.get_droplets()

        if required_droplet not in existing_droplets:
            api.create_droplet(required_droplet)

        droplets_to_remove = (
                droplet for droplet in existing_droplets
                if droplet != required_droplet
        )
        api.remove_droplets(droplets_to_remove)

