from flask import Flask
import json
from docker import Client
import random
import string

app = Flask(__name__)
docker = Client(version='1.10')

# TODO: we should collect the types of services that we provide in some kind of registry that the Flask app can collect

images = {'joai': 'joai_bv:latest', 'mysql': 'mysql:latest', 'nginx': 'nginx:latest'}


@app.route('/')
def main_page():
    containers = []
    for container in docker.containers():
        for image in images.keys():
            if container['Image'] == images[image]:
                containers.append(container)
    ids = map(lambda item: item['Id'], containers)
    return json.dumps(ids), 200


@app.route('/factory', methods=['GET'])
def get_services():
    return json.dumps(images.keys()), 200


# don't know whether this is a good way, feel free to comment on this.
@app.route('/factory/<service>', methods=['POST'])
def create_new(service):
    if service in images.keys():
        container = get_container(service)
        try:
            docker.start(container, publish_all_ports=True)
        except NotImplementedError:
            return 'Container type not available', 404
        #why are we doing this?
        container['Status'] = 'Creating'
        return json.dumps(container), 201
    else:
        return 'Container type not available', 404


@app.route('/<id>', methods=['GET'])
def get_container(id):
    try:
        container = docker.inspect_container({'Id': id})
    except:
        return 'Container not found', 404

    ret = dict()
    #why this is ID and not Id?
    ret['Id'] = container['ID']
    ret['State'] = container['State']
    if container['NetworkSettings']['Ports']:
        ret['Connection'] = {}
        for index, portdesc in enumerate(container['NetworkSettings']['Ports'].keys()):
             ret['Connection']['HostPort%i' % index] = container['NetworkSettings']['Ports'][portdesc][0]['HostPort']
        #it should be something else, set by the providing host.
        ret['Connection']['HostIp'] = '0.0.0.0'

    ret['Password'] = extract_pass(container)
    return json.dumps(ret)


@app.route('/<container_id>', methods=['DELETE'])
def delete_container(container_id):
    try:
        container = docker.inspect_container({'Id': id})
    except:
        return 'Container not found', 404

    docker.stop(container)


def get_container(service):
    if service == 'mysql':
        password = generate_pass(10)
        return docker.create_container(images['mysql'], environment=['MYSQL_ROOT_PASSWORD=%s' % password])
    elif service == 'joai':
        return docker.create_container(images['joai'])
    elif service == 'nginx':
        return docker.create_container(images['nginx'])
    else:
        raise NotImplementedError


def generate_pass(length):
    return ''.join(random.choice(string.ascii_uppercase + string.lowercase + string.digits) for i in range(length))


def extract_pass(container):
    env = container['Config']['Env']
    word = filter(lambda item: item.count('MYSQL_ROOT_PASSWORD') > 0, env)
    if word:
        word = word[0].split('=')
        return word[1]
