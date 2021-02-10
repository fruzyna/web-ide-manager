#!/bin/bash

proxypath=$(<config/proxy_path)
domain=$(<config/domain)
guipath=$(<config/gui_path)
guiport=$(<config/gui_port)

config=$(<config/code.subfolder.conf.sample)
config="${config/DOMAIN/$domain}"
config="${config//NAME/$guipath}"
config="${config/CONTAINER_PORT/$guiport}"
tee ${proxypath}/${guipath}.code.subfolder.conf <<< $config

docker restart reverse-proxy