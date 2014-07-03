from flask import Flask
import json
from docker import Client
import random
import string

app = Flask(__name__)
docker = Client(version='1.10')

@app.route('/')
def main_page():
  containers = filter(lambda item: item['Image'].count('mysql')>0, docker.containers())
  ids = map(lambda item: item['Id'], containers)
  return json.dumps(ids), 200

@app.route('/', methods=['POST'])
def create_new():
  container = get_mysql_container()
  docker.start(container, publish_all_ports=True)
  container['Status'] = 'Created'
  return json.dumps(container), 201

@app.route('/<id>', methods=['GET'])
def get_container(id):
  try:
    container = docker.inspect_container({'Id':id})
  except:
    return 'Container not found', 404
  
  ret = dict()
  #why this is ID and not Id?
  ret['Id'] = container['ID']
  ret['State'] = container['State']
  if container['NetworkSettings']['Ports']:
    ret['Connection'] = container['NetworkSettings']['Ports']['3306/tcp']
    #it should be something else
    ret['Connection']['HostIp'] = '0.0.0.0'
  
  ret['Password'] = extract_pass(container)
  return json.dumps(ret)
 
@app.route('/<id>', methods=['DELETE'])
def delete_container(id):
  try:
    container = docker.inspect_container({'Id':id})
  except:
    return 'Container not found', 404
  
  docker.stop(container)
 

def get_mysql_container():  
  password = generate_pass(10)
  mysql_container = docker.create_container('mysql', environment=['MYSQL_ROOT_PASSWORD=%s' % password])
  return mysql_container

def generate_pass(length):
  return ''.join(random.choice(string.ascii_uppercase + string.lowercase + string.digits) for i in range(length))


def extract_pass(container):
  env = container['Config']['Env']
  word = filter(lambda item: item.count('MYSQL_ROOT_PASSWORD')>0, env)
  if word:
    word = word[0].split('=')
    return word[1]
 
