# web-ide-manager

My Web IDE Manager is a webapp designed to help create and manage instances of code-server, jupyter, and other dockerize web IDEs.

## gui.py Web GUI

The server can operate through a reverse proxy and has a `setup-gui.sh` script to prepare the config file and restart the proxy. Speaking of which the index of the GUI allows creation of a new instance at a path of the submitted name. This page can be secured with an access code set at `config/gui_password`. The `/status` page allows stopping, restarting, and removing of currently created containers. The new Flask server can be started with `FLASK_APP=gui/gui.py python3 -m flask run --host=0.0.0.0`.

## Configuration

The app is configured using a series of config files in /config. A dictionary for these files is provided below.

| file            | description |
| --------------- | ----------- |
| admin_password  | Access code necessary to create change advanced options. |
| domain          | The domain where the server is externally accessible, e.g. www.example.com. |
| gui_password    | Access code necessary to create new instances. |
| gui_path        | Subfolder where GUI is accessible, e.g. init. |
| gui_port        | Port where GUI is accessible, default is 8110. |
| max_port        | Maximum port number the GUI can assign to a container, default is 8111. |
| min_port        | Minimum port number the GUI can assign to a container, default is 8120. |
| proxy_container | Name of the reverse proxy container. |
| proxy_path      | Path of proxy config files. |
| sudo_password   | Password to use for instances' sudo users. |