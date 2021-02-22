from flask import Flask, render_template, jsonify, request
import subprocess, json, os, socket

# read config options
def read_config(path):
    config = ''
    with open(path, 'r') as f:
        config = f.read().rstrip()
    return config

PORT = int(read_config('config/gui_port'))
MIN_PORT = int(read_config('config/min_port'))
MAX_PORT = int(read_config('config/max_port'))
DOMAIN = read_config('config/domain')
PROXY_PATH = read_config('config/proxy_path')
PROXY_CONTAINER = read_config('config/proxy_container')
SUDO_PASSWORD = read_config('config/sudo_password').lower()
GUI_PASSWORD = read_config('config/gui_password').lower()
ADMIN_PASSWORD = read_config('config/admin_password').lower()
SERVER_PATH = read_config('config/gui_path')
EXTERNAL_URL = read_config('config/domain')

SERVER_PATH = '/' + SERVER_PATH if SERVER_PATH != '' else ''

# create flask app
app = Flask(__name__)

# load in image details
images = {}
with open('gui/images.json') as f:
    images = json.load(f)

# make filters for docker commands
filters = []
for name in images.keys():
    filters += ['--filter', 'name={}-*'.format(name)]

@app.route('/')
def index():
    options = [ { 'name': i, 'friendly': images[i]['name'] } for i in images.keys() ]
    return render_template('index.html', admin_code=ADMIN_PASSWORD, pass_code=GUI_PASSWORD, images=options)

def buildInstances(asList=False):
    # get container status
    status_strs = str(subprocess.check_output(['docker', 'container', 'ls', '-a', '--format', '{{.Names}} {{.Status}} {{.Ports}}'] + filters))[2:-1].split('\\n')

    instances = {}
    if asList:
        instances = []

    for line in status_strs:
        if line.count(' ') >= 2:
            words = line.split()
            if words[-1] == '':
                words.pop()

            name = words[0]

            # determine uptime
            if ':' in words[-1]:
                uptime = words[1:-1]
            else:
                uptime = words[1:]
            if uptime[0] == 'Up':
                uptime = ' '.join(uptime[1:])
            elif uptime:
                uptime = uptime[0]
            
            # determine port number
            port = words[-1]
            if ':' in port and '-' in port:
                port = port[port.index(':')+1:port.index('-')]
            else:
                port = ''
            
            # determine volume name, use source if not named (not a volume)
            volume = str(subprocess.check_output(['docker', 'inspect', '-f', '{{(index .Mounts 0).Name}}', name]))[2:-3]
            print("'" + volume + "'")
            if not volume:
                volume = str(subprocess.check_output(['docker', 'inspect', '-f', '{{(index .Mounts 0).Source}}', name]))[2:-3]

            # create instance object
            if asList:
                instances.append({
                'name': name,
                'uptime': uptime,
                'volume': volume,
                'port': port
                })
            else:
                instances[name] = {
                    'uptime': uptime,
                    'volume': volume,
                    'port': port
                }
    
    return instances

@app.route('/status')
def status():
    return render_template('status.html', internal_addr='http://{}'.format(socket.gethostbyname(socket.gethostname())), external_addr='https://{}'.format(DOMAIN), instances=buildInstances(asList=True))

@app.route('/getInstances')
def getInstances():
    return buildInstances()

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

        # extract name and image
        words = name.split('-')
        name = words[-1]
        image = '-'.join(words[:-1])

        # delete proxy config
        if EXTERNAL_URL and PROXY_PATH:
            config = '{0}/{1}.{2}.subfolder.conf'.format(PROXY_PATH, name, image)
            if os.path.exists(config):
                os.remove(config)

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
                port = str(p)
                break

        # determine taken names
        name_str = str(subprocess.check_output(['docker', 'container', 'ls', '--format', '{{.Names}}'] + filters))[2:-1]
        names = [ name for name in name_str.split('\\n') if '-' in name ]
        
        # check for valid inputs
        if not name.isalnum() or '{0}-{1}'.format(image, name) in names:
            return '<h1>Invalid name</h1>'
        if not password.isalnum():
            return '<h1>Invalid password</h1>'

        # determine volume
        if 'volume' in request.args:
            volume = request.args['volume']
        else:
            volume = '{0}-{1}-vol'.format(image, name)
            subprocess.check_output(['docker', 'volume', 'create', volume])

        # determine resource limitations
        if 'cpus' in request.args and 'memory' in request.args and 'swap' in request.args:
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
        if 'command' in imageInfo:
            command += imageInfo['command'].replace('{{ password }}', password).replace('{{ sudo_password }}', SUDO_PASSWORD).split(' ')

        subprocess.check_output(command)

        # determine URL
        ip = socket.gethostbyname(socket.gethostname())
        url = 'http://{0}:{1}'.format(ip, port)
        if EXTERNAL_URL and PROXY_PATH:
            path = '{0}/{1}'.format(name, image)
            url = 'https://{0}/{1}'.format(EXTERNAL_URL, path)

            # create proxy config
            config = ''
            with open('config/subfolder.conf.sample', 'r') as f:
                config = f.read().replace('DOMAIN', EXTERNAL_URL).replace('NAME', path).replace('CONTAINER_PORT', port)
            with open('{0}/{1}.{2}.subfolder.conf'.format(PROXY_PATH, name, image), 'w') as f:
                f.write(config)
            if PROXY_CONTAINER:
                subprocess.check_output(['docker', 'restart', PROXY_CONTAINER])

        return '<meta http-equiv="refresh" content="10; URL={0}" /><h1>Redirecting to {1} in 10 seconds</h1><a href="{0}">{0}</a>'.format(url, image)

    return 'Invalid request'