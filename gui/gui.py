from flask import Flask, render_template, jsonify, request
import subprocess, json, os, socket, hashlib

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
GUI_PASSWORD = hashlib.sha512(read_config('config/gui_password').lower().encode('utf-8')).hexdigest()
ADMIN_PASSWORD = hashlib.sha512(read_config('config/admin_password').lower().encode('utf-8')).hexdigest()
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
    return render_template('index.html', images=options, gui_path=SERVER_PATH)

def buildInstances(asList=False, owner=''):
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
            if not name.endswith(owner):
                continue
            image = '-'.join(name.split('-')[:-1])
            words = words[1:]

            # determine port number(s)
            port = ''
            devPort = ''
            first = len(words)
            for i, word in enumerate(words):
                if ':' in word and '->' in word:
                    extp = int(word[word.rindex(':')+1:word.index('-')])
                    intp = int(word[word.index('>')+1:word.index('/')])
                    if intp == images[image]['port']:
                        port = extp
                    else:
                        devPort = extp
                    if i < first:
                        first = i
            
            # determine uptime
            uptime = ' '.join(words[:first])
            
            # determine volume name, use source if not named (not a volume)
            try:
                volume = str(subprocess.check_output(['docker', 'inspect', '-f', '{{(index .Mounts 0).Name}}', name]))[2:-3]
                if not volume:
                    volume = str(subprocess.check_output(['docker', 'inspect', '-f', '{{(index .Mounts 0).Source}}', name]))[2:-3]
            except Exception as e:
                volume = ''

            # create instance object
            if asList:
                instances.append({
                'name': name,
                'uptime': uptime,
                'volume': volume,
                'port': port,
                'devPort': devPort
                })
            else:
                instances[name] = {
                    'uptime': uptime,
                    'volume': volume,
                    'port': port,
                    'devPort': devPort
                }
    
    return instances

@app.route('/checkcode')
def checkCode():
    hashed = request.args.get('hash')
    if hashed == ADMIN_PASSWORD:
        return "admin"
    elif hashed == GUI_PASSWORD:
        return "gui"
    return "none"

@app.route('/status')
def status():
    owner = request.args.get('name')
    hashed = request.args.get('hash')
    if not owner:
        owner = ''
    instances = []
    if hashed == ADMIN_PASSWORD or hashed == GUI_PASSWORD:
        instances = buildInstances(asList=True, owner=owner)
    return render_template('status.html', internal_addr='http://{}'.format(socket.gethostbyname(socket.gethostname())), external_addr='https://{}'.format(DOMAIN), instances=instances, gui_path=SERVER_PATH)

@app.route('/getInstances')
def getInstances():
    return buildInstances()

@app.route('/start')
def start():
    name = request.args['name']
    if name:
        # start container
        subprocess.Popen(['docker', 'start', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/stop')
def stop():
    name = request.args['name']
    if name:
        # stop container
        subprocess.Popen(['docker', 'stop', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/remove')
def remove():
    name = request.args['name']
    if name:
        # remove container
        subprocess.check_output(['docker', 'stop', name])
        subprocess.Popen(['docker', 'rm', name])

        # extract name and image
        words = name.split('-')
        name = words[-1]
        image = '-'.join(words[:-1])

        # delete proxy config
        if EXTERNAL_URL and PROXY_PATH:
            config = '{0}/{1}.{2}.subfolder.conf'.format(PROXY_PATH, name, image)
            if os.path.exists(config):
                os.remove(config)
            # remove dev url config
            config = '{0}/{1}-dev.{2}.subfolder.conf'.format(PROXY_PATH, name, image)
            if os.path.exists(config):
                os.remove(config)

        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

def findPort(skip=''):
    # find all allocated ports from other web ide containers
    ports = []
    port_lines = str(subprocess.check_output(['docker', 'container', 'ls', '-a', '--format', '{{.Ports}}'] + filters))[2:-1].split('\\n')
    for line in port_lines:
        for port_str in line.split(', '):
            if ':' in port_str and '->' in port_str:
                ports.append(int(port_str[port_str.rindex(':')+1:port_str.index('-')]))

    port = -1
    # find holes in assigned ports, there is an issue here with stopped instances
    for p in range(MIN_PORT, MAX_PORT+1):
        if p not in ports and str(p) != skip:
            port = str(p)
            break
    return port

def makeProxyConf(forwardPath, name, image, port):
    # create proxy config
    path = '{0}/{1}'.format(name, image)
    config = ''
    with open('config/subfolder.conf.sample', 'r') as f:
        fpath = ''
        if forwardPath:
            fpath = '/{}'.format(path)
        config = f.read().replace('DOMAIN', EXTERNAL_URL).replace('NAME', path).replace('CONTAINER_PORT', port).replace('PATH', fpath)
    with open('{0}/{1}.{2}.subfolder.conf'.format(PROXY_PATH, name, image), 'w') as f:
        f.write(config)
    return path

@app.route('/createInstance')
def createInstance():
    if 'name' in request.args.keys() and 'password' in request.args.keys() and 'image' in request.args.keys() and 'hash' in request.args.keys():
        name = request.args['name']
        password = request.args['password']
        image = request.args['image']
        imageInfo = images[image]
        hashed = request.args['hash']

        # determine next port
        port = findPort()

        # determine taken names
        name_str = str(subprocess.check_output(['docker', 'container', 'ls', '--format', '{{.Names}}'] + filters))[2:-1]
        names = [ name for name in name_str.split('\\n') if '-' in name ]
        
        # check for valid inputs
        if not name.isalnum() or '{0}-{1}'.format(image, name) in names:
            return '<h1>Invalid name</h1>'
        if not password.isalnum():
            return '<h1>Invalid password</h1>'
        if hashed != ADMIN_PASSWORD and hashed != GUI_PASSWORD:
            return '<h1>Invalid passcode</h1>'

        # determine volume
        if 'volume' in request.args:
            volume = request.args['volume']
            if not os.path.exists(volume):
                os.mkdir(volume)
                os.chown(volume, 1000, 1000)
        else:
            volume = '{0}-{1}-vol'.format(image, name)
            subprocess.check_output(['docker', 'volume', 'create', volume])

        # determine resource limitations
        if 'cpus' in request.args and 'memory' in request.args and 'swap' in request.args and hashed == ADMIN_PASSWORD:
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

        # allocate an additional web port
        devport = ''
        if 'port' in request.args:
            devport = findPort(port)
            command += ['-p', '{}:{}'.format(devport, request.args['port'])]

        # add environment variables
        for e in imageInfo['environment']:
            e = e.replace('{{ password }}', password).replace('{{ sudo_password }}', SUDO_PASSWORD).replace('{{ name }}', name)
            command += ['-e', '{}'.format(e)]

        # add image name
        command += [imageInfo['image']]

        path = ''
        if EXTERNAL_URL and PROXY_PATH:
            path = '{0}/{1}'.format(name, image)

        # add optional command
        if 'command' in imageInfo:
            command += imageInfo['command'].replace('{{ password }}', password).replace('{{ sudo_password }}', SUDO_PASSWORD).replace('{{ path }}', path).replace('{{ name }}', name).split(' ')

        subprocess.Popen(command)

        # determine URL
        ip = socket.gethostbyname(socket.gethostname())
        url = 'http://{0}:{1}'.format(ip, port)
        devurl = ''
        if devport:
            devurl = 'http://{0}:{1}'.format(ip, devport)
        if EXTERNAL_URL and PROXY_PATH:
            # create proxy configs
            path = makeProxyConf('forward-path' in imageInfo and imageInfo['forward-path'], name, image, port)
            url = 'https://{0}/{1}'.format(EXTERNAL_URL, path)

            if devport:
                path = makeProxyConf(True, '{}-dev'.format(name), image, devport)
                devurl = 'https://{0}/{1}'.format(EXTERNAL_URL, path)

            if PROXY_CONTAINER:
                subprocess.Popen(['docker', 'restart', PROXY_CONTAINER])
        
        return render_template('launch.html', instance=image, link=url, dev_link=devurl)

    return 'Invalid request'