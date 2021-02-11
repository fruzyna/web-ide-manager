import socketserver, http.server, subprocess, socket, os

def read_config(path):
    config = ''
    with open(path, 'r') as f:
        config = f.read().rstrip()
    return config

PORT = int(read_config('config/gui_port'))
MIN_PORT = int(read_config('config/min_port'))
MAX_PORT = int(read_config('config/max_port'))

PASSWORD = read_config('config/gui_password').lower()
SERVER_PATH = read_config('config/gui_path')
EXTERNAL_URL = read_config('config/domain')

SERVER_PATH = '/' + SERVER_PATH if SERVER_PATH != '' else ''

images = [n[n.index('-')+1 : n.rindex('-')] for n in list(filter(lambda n: n.count('-') > 1, os.listdir('management')))]
filters = [['--filter', 'name={}-*'.format(i)] for i in images]
filters = [i for l in filters for i in l]

class ServerHandler(http.server.SimpleHTTPRequestHandler):

    # default response
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def send_res(self, html_str):
        self._set_response()
        self.wfile.write(str.encode(html_str))

    def do_GET(self):
        # process query
        queries = self.path.split('?')
        if len(queries) > 1:
            queries = queries[1].split('&')
            query = {}
            for q in queries:
                parts = q.split('=')
                query[parts[0]] = parts[1].lower()

        if self.path.startswith('/index.html') or self.path == '/':
            options = ''.join(['<option value="{0}">{0}</option>'.format(i) for i in images])
            body = '<form action="{0}/createInstance" id="body">'\
                '<label for="code">Access Code: </label>'\
                '<input type="password" name="code" value=""><br><br>'\
                '<label for="image">Image: </label>'\
                '<select name="image" id="image" form="body">{1}'\
                '</select>'\
                '<br><br>'\
                'Use only lowercase letters and numbers for the name and password.<br><br>'\
                '<label for="name">First Name: </label>'\
                '<input type="text" name="name" value=""><br><br>'\
                '<label for="password">Password: </label>'\
                '<input type="password" name="pass" value=""><br><br>'\
                '<input type="submit" value="Create Instance">'\
            '</form>'.format(SERVER_PATH, options)
            with open('gui/index.html', 'r') as f:
                self.send_res(f.read().replace('BODY', body))
            return

        if self.path.startswith('/stop'):
            if query['name']:
                # stop container and send redirect
                status_strs = str(subprocess.check_output(['docker', 'stop', query['name']]))
                self.send_res('<meta http-equiv="refresh" content="10; URL={0}/status" />'.format(SERVER_PATH))
            else:
                self.send_res('<h1>Error no name provided</h1>')
            return

        if self.path.startswith('/start'):
            if query['name']:
                # start container and send redirect
                status_strs = str(subprocess.check_output(['docker', 'start', query['name']]))
                self.send_res('<meta http-equiv="refresh" content="10; URL={0}/status" />'.format(SERVER_PATH))
            else:
                self.send_res('<h1>Error no name provided</h1>')
            return

        if self.path.startswith('/remove'):
            if query['name']:
                # remove container and send redirect
                words = query['name'].split('-')
                image = '-'.join(words[:-1])
                name = words[-1]
                status_strs = str(subprocess.check_output(['management/remove-instance.sh', image, name]))
                self.send_res('<meta http-equiv="refresh" content="10; URL={0}/status" />'.format(SERVER_PATH))
            else:
                self.send_res('<h1>Error no name provided</h1>')
            return

        if self.path.startswith('/status'):
            # get container status
            status_strs = str(subprocess.check_output(['docker', 'container', 'ls', '-a', '--format', '{{.Names}} {{.Status}} {{.Ports}}'] + filters))[2:-1].split('\\n')
            
            # build table
            table = '<table id="body"><tr><td>Name</td><td>Uptime</td><td>Port</td><td></td><td></td><td></td><td></td></tr>'
            for line in status_strs:
                if line.count(' ') >= 2:
                    words = line.split()
                    name = words[0]
                    if ':' in words[-1]:
                        uptime = words[1:-1]
                    else:
                        uptime = words[1:]
                    control = ''
                    remove = ''
                    if len(uptime) == 3 and uptime[0] == 'Up':
                        uptime = ' '.join(uptime[1:3])
                        control = '<a href="{0}/stop?name={1}">Stop</a>'.format(SERVER_PATH, words[0])
                    elif uptime:
                        uptime = uptime[0]
                        control = '<a href="{0}/start?name={1}">Resume</a>'.format(SERVER_PATH, words[0])
                        remove = '<a href="{0}/remove?name={1}">Remove</a>'.format(SERVER_PATH, words[0])
                    port = words[-1]
                    if ':' in port and '-' in port:
                        port = port[port.index(':')+1:port.index('-')]
                    else:
                        port = ''
                    ip = socket.gethostbyname(socket.gethostname())
                    external_url = '<a href="https://{1}/{0}">External Link</a>'.format(name, EXTERNAL_URL) if EXTERNAL_URL else ''
                    table += '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td><a href="http://{3}:{2}">Internal Link</a></td><td>{6}</td><td>{4}</td><td>{5}</td></tr>'.format(name, uptime, port, ip, control, remove, external_url)
            table += '</table>'

            # send table
            with open('gui/index.html', 'r') as f:
                self.send_res(f.read().replace('BODY', table))
            return

        if self.path.startswith('/createInstance'):

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

            # check for correct parameters
            if port >= MIN_PORT and port <= MAX_PORT:
                if 'image' in query:
                    if 'name' in query and query['name'].isalnum() and '{0}-{1}'.format(query['image'], query['name']) not in names:
                        if 'pass' in query and query['pass'].isalnum():
                            if 'code' in query and query['code'] == PASSWORD:
                                # launch
                                subprocess.Popen(['management/create-instance.sh', query['image'], query['name'], query['pass'], str(port)])
                                ip = socket.gethostbyname(socket.gethostname())
                                url = 'http://{0}:{1}</a>'.format(ip, port)
                                if EXTERNAL_URL:
                                    url = 'https://{0}/{1}</a>'.format(EXTERNAL_URL, query['name'])

                                # send redirect page
                                self.send_res('<meta http-equiv="refresh" content="10; URL={0}" /><h1>Redirecting to {1} in 10 seconds</h1><a href="{0}">{0}</a>'.format(url, query['image']))
                                return
                            else:
                                self.send_res('<h1>Invalid access code</h1>')
                                return
                        else:
                            self.send_res('<h1>Invalid password</h1>')
                            return
                    else:
                        self.send_res('<h1>Invalid name</h1>')
                        return
                else:
                    self.send_res('<h1>Invalid image</h1>')
                    return
            else:
                self.send_res('<h1>Error assigning port</h1>')
                return

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

# start HTTP server
Handler = ServerHandler
httpd = socketserver.TCPServer(('', PORT), Handler)
print('Serving at port: ', PORT)
httpd.serve_forever()