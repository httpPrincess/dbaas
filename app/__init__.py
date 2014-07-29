from flask import Flask
from flask import jsonify, abort
from docker import Client
import random
import string
import importlib

app = Flask(__name__)
app.config.from_object('config')
docker = Client(version='1.10')

try:
    auth = importlib.import_module(app.config.get('AUTH_MIDDLEWARE'))
except ImportError:
    app.logger.error('Error while loading authentication middleware')
    exit(1)

# TODO: we should collect the types of services that we provide in some kind of registry that the Flask app can collect
images = {'joai': 'joai_bv:latest', 'mysql': 'mysql:latest', 'nginx': 'nginx:latest'}


@app.route('/', methods=['GET'])
def get_services():
    return jsonify(services=get_service_list()), 200


@app.route('/<service>/', methods=['GET'])
def main_page(service):
    containers = []
    if service not in get_service_list():
      abort(404)
      
    for container in docker.containers():
        if container['Image'].split(':')[0] == images[service].split(':')[0]:
                containers.append(container)
    ids = map(lambda item: item['Id'], containers)
    return jsonify(instances=ids)


@app.route('/<service>/', methods=['POST'])
@auth.requires_auth
def create_new(service):
    if service in get_service_list():
        container = get_container(service)
        try:
            docker.start(container, publish_all_ports=True)
        except NotImplementedError:
            return 'Container type not available', 404
        container['Status'] = 'Creating'
        return jsonify(instance=container), 201
    else:
        return 'Container type not available', 404


@app.route('/<service>/<id>', methods=['GET'])
def get_container(service, id):
    container = get_running_container(service, id)
    if not container:
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
    return jsonify(instance=ret)


@app.route('/<service>/<id>', methods=['DELETE'])
@auth.requires_auth
def delete_container(service, id):
    container = get_running_container(service, id) 
    if not container:
        return 'Container not found', 404
    container['Id']=container['ID']
    docker.stop(container)
    return 'Removed', 404


def get_service_list():
    return images.keys()


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


def get_running_container(service, id):
    try:
        container = docker.inspect_container({'Id': id})
        if container['Config']['Image'].split(':')[0]!=images[service].split(':')[0]:
            raise Exception('Wrong container type')
        return container
    except Exception:
        None


def generate_pass(length):
    return ''.join(random.choice(string.ascii_uppercase + string.lowercase + string.digits) for i in range(length))


def extract_pass(container):
    env = container['Config']['Env']
    word = filter(lambda item: item.count('MYSQL_ROOT_PASSWORD') > 0, env)
    if word:
        word = word[0].split('=')
        return word[1]
