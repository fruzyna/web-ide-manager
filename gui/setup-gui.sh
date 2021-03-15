#!/bin/bash

cp web-ide-manager.service /etc/systemd/system
sudo systemctl enable web-ide-manager.service
sudo systemctl start web-ide-manager.service

proxypath=$(<config/proxy_path)
domain=$(<config/domain)
guipath=$(<config/gui_path)
guiport=$(<config/gui_port)

config=$(<config/code.subfolder.conf.sample)
config="${config/DOMAIN/$domain}"
config="${config//NAME/$guipath}"
config="${config//PATH/$guipath}"
config="${config/CONTAINER_PORT/$guiport}"
tee ${proxypath}/${guipath}init.code.subfolder.conf <<< $config

docker restart reverse-proxy