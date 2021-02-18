from flask import Flask, render_template, jsonify, request
import subprocess, json, os

def read_config(path):
    config = ''
    with open(path, 'r') as f:
        config = f.read().rstrip()
    return config

PORT = int(read_config('../../config/gui_port'))
MIN_PORT = int(read_config('../../config/min_port'))
MAX_PORT = int(read_config('../../config/max_port'))

SUDO_PASSWORD = read_config('../../config/sudo_password').lower()
PASSWORD = read_config('../../config/gui_password').lower()
SERVER_PATH = read_config('../../config/gui_path')
EXTERNAL_URL = read_config('../../config/domain')

SERVER_PATH = '/' + SERVER_PATH if SERVER_PATH != '' else ''

app = Flask(__name__)

images = {}
with open('images.json') as f:
    images = json.load(f)

@app.route('/')
def index():
    options = [ { 'name': i, 'friendly': images[i]['name'] } for i in images.keys() ]
    return render_template('index.html', admin_code=GUI_PASSWORD, pass_code=GUI_PASSWORD, images=options)

@app.route('/status')
def status():
    instances = [{ 'name': 'code-server-liam', 'uptime': 'Up 3 hours', 'volume': 'cs-liam-vol', 'port': 8111 },
                 { 'name': 'code-server-test', 'uptime': 'Up 1 hours', 'volume': '/code', 'port': 8112 },
                 { 'name': 'jupyter-liam', 'uptime': 'Stopped', 'volume': 'jnb-liam-vol', 'port': 8113 },
                 { 'name': 'frc-java-test', 'uptime': 'Up 5 minutes', 'volume': 'frc-test-vol', 'port': 8114 }]
    return render_template('status.html', internal_addr='http://localhost', external_addr='https://wildstang.dev', instances=instances)

@app.route('/getInstances')
def getInstances():
    return jsonify({'code-server-liam': { 'uptime': 'Up 3 hours', 'volume': 'cs-liam-vol', 'port': 8111 },
                    'code-server-test': { 'uptime': 'Up 1 hours', 'volume': '/code', 'port': 8112 },
                    'frc-java-test': { 'uptime': 'Up 5 minutes', 'volume': 'frc-test-vol', 'port': 8114 }})

@app.route('/start')
def start():
    name = request.args['name']
    if name:
        # start container
        subprocess.check_output(['docker', 'start', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/stop')
def stop():
    name = request.args['name']
    if name:
        # stop container
        subprocess.check_output(['docker', 'stop', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/remove')
def remove():
    name = request.args['name']
    if name:
        # remove container
        subprocess.check_output(['docker', 'stop', name])
        subprocess.check_output(['docker', 'rm', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/createInstance')
def createInstance():
    if 'name' in request.args.keys() and 'password' in request.args.keys() and 'image' in request.args.keys():
        name = request.args['name']
        password = request.args['password']
        image = request.args['image']
        imageInfo = images[image]

        # determine next port
        port_str = str(subprocess.check_output(['docker', 'container', 'ls', '--format', '{{.Ports}}'] + filters))[2:-1]
        ports = [ int(port[port.index(':')+1:port.index('-')]) for port in port_str.split('\\n') if ':' in port and '-' in port ]
        port = -1
        # find holes in assigned ports, there is an issue here with stopped instances
        for p in range(MIN_PORT, MAX_PORT+1):
            if p not in ports:
                port = p
                break

        # determine taken names
        name_str = str(subprocess.check_output(['docker', 'container', 'ls', '--format', '{{.Names}}'] + filters))[2:-1]
        names = [ name for name in name_str.split('\\n') if '-' in name ]
        
        # check for valid inputs
        if not name.isalnum() or '{0}-{1}'.format(query['image'], query['name']) in names:
            return '<h1>Invalid name</h1>'
        if not password.isalnum():
            return '<h1>Invalid password</h1>'

        # determine volume
        if 'volume' in request.args.keys():
            volume = request.args['volume']
        else:
            volume = '{0}-{1}-vol'.format(image, name)
            subprocess.check_output(['docker', 'volume', 'create', volume])

        # determine resource limitations
        if 'cpus' in request.args.keys() and 'memory' in request.args.keys() and 'swap' in request.args.keys():
            cpus = request.args['cpus']
            memory = request.args['memory']
            swap = request.args['swap']
        else:
            cpus = imageInfo['cpus']
            memory = imageInfo['memory']
            swap = imageInfo['swap']

        # build command
        command = ['docker', 'run', '-d', '--name', '{0}-{1}'.format(image, name), 
            '-p', '{0}:{1}'.format(port, imageInfo['port']), '--restart', 'unless-stopped',
            '-v', '{0}:{1}'.format(volume, imageInfo['volume']), '--cpus', str(cpus),
            '-m', '{}g'.format(memory), '--memory-swap', '{}g'.format(swap)]

        # add environment variables
        for e in imageInfo['environment']:
            e = e.replace('{{ password }}', password).replace('{{ sudo_password }}', SUDO_PASSWORD)
            command += ['-e', '"{}"'.format(e)]

        # add image name
        command += [imageInfo['image']]

        # add optional command
        if 'command' in request.args.keys():
            command += imageInfo['command'].replace('{{ password }}', password).replace('{{ sudo_password }}', SUDO_PASSWORD).split(' ')

        subprocess.check_output(command)

        # determine URL
        ip = socket.gethostbyname(socket.gethostname())
        url = 'http://{0}:{1}'.format(ip, port)
        if EXTERNAL_URL:
            url = 'https://{0}/{1}/{2}'.format(EXTERNAL_URL, name, image)
        return '<meta http-equiv="refresh" content="10; URL={0}" /><h1>Redirecting to {1} in 10 seconds</h1><a href="{0}">{0}</a>'.format(url, image)
    return 'Invalid request'