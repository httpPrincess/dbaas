from flask import Flask
import json
from docker import Client
import random
import string

app = Flask(__name__)
docker = Client(version='1.10')

@app.route('/')
def main_page():
  print 'Retrieving containers'
  containers = filter(is_our_container, docker.containers())
  ids = map(extract_id, containers)
  return json.dumps(ids), 200

@app.route('/', methods=['POST'])
def create_new():
  print 'Creating new instance...'
  container = get_mysql_container()
  docker.start(container, publish_all_ports=True)
  return 'Accepted', 201

@app.route('/<id>', methods=['GET'])
def get_container(id):
  print 'Retrieving instance %s' % id
  try:
    container = docker.inspect_container({'Id':id})
  except:
    return 'Container not found', 404
  
  ret = dict()
  #why this is ID and not Id?
  ret['Id'] = container['ID']
  ret['State'] = container['State']
  ret['Connection'] = container['NetworkSettings']
  #jj: manual 
  ret['Connection']['HostIp'] = '0.0.0.0'
  ret['Password'] = extract_pass(container)
   
  return json.dumps(ret)
 
@app.route('/<id>', methods=['DELETE'])
def delete_container(id):
  print 'Deleting instance %s' % id
  try:
    container = docker.inspect_container({'Id':id})
  except:
    return 'Container not found', 404
  
  docker.stop(container)
 

def get_mysql_container():
  password = ''.join(random.choice(string.ascii_uppercase + string.lowercase + string.digits) for i in range(10))
  mysql_container = docker.create_container('mysql', environment=['MYSQL_ROOT_PASSWORD=%s' % password])
  return mysql_container

def is_our_container(item):
  return item['Image'].count('mysql')>0

def extract_id(item):
  return item['Id']

def extract_pass(container):
  env = container['Config']['Env']
  word = filter(lambda item: item.count('MYSQL_ROOT_PASSWORD')>0, env)
  if word:
    word = word[0].split('=')
    return word[1]
 
