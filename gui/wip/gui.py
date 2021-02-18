from flask import Flask, render_template, jsonify, request
import subprocess, json
app = Flask(__name__)

images = {}
with open('images.json') as f:
    images = json.load(f)

@app.route('/')
def index():
    options = [ { 'name': i, 'friendly': images[i]['name'] } for i in images.keys() ]
    return render_template('index.html', admin_code='admincode', pass_code='accesscode', images=options)

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
        # stop container
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
        # stop container
        subprocess.check_output(['docker', 'stop', name])
        subprocess.check_output(['docker', 'rm', name])
        return getInstances()
    else:
        return '<h1>Error no name provided</h1>', 400

@app.route('/createInstance')
def createInstance():
    name = request.args['name']
    password = request.args['password']
    image = request.args['image']
    cpus = request.args['cpus']
    memory = request.args['memory']
    swap = request.args['swap']
    volume = request.args['volume']
    command = ''
    if name and password and image:
        imageInfo = images[image]
        if not volume:
            volume = '{0}-{1}-vol'.format(image, name)
        if not cpus or not memory or not swap:
            cpus = imageInfo['cpus']
            memory = imageInfo['memory']
            swap = imageInfo['swap']
        command = ['docker', 'run', '-d', '--name', '{0}-{1}'.format(image, name), 
            '-p', '{0}:{1}'.format(8111, imageInfo.port), '--restart', 'unless-stopped',
            '-v', '{0}:{1}'.format(volume, imageInfo.volume), '--cpus', cpus,
            -m, '{}g'.format(memory), '--memory-swap', '{}g'.format(swap)]
        for e in imageInfo['environment']:
            command += ['-e', e]
        command += [imageInfo['image']]
        if imageInfo['command']:
            command += imageInfo['command'].split(' ')

        print(' '.join(command))
    return ' '.join(command)