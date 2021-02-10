#!/bin/bash

name=$1
pass=$2
port=$3

proxy_path=$(<config/proxy_path)
domain=$(<config/domain)
sudo=$(<config/sudo_password)
proxy_container=$(<config/proxy_container)

container_name=jupyter-${name}
volume_name=jnb-${name}-vol

# TODO create volume of limited size, without overwriting contents of /config
docker volume create $volume_name

# start docker container
docker run -d --name $container_name \
			-e JUPYTER_ENABLE_LAB=yes \
			-p $port:8888 \
		    --cpus 0.5 -m 2.0g --memory-swap 5g \
			-v $volume_name:/home/jovyan \
		   --restart unless-stopped \
			jupyter/datascience-notebook \
			start.sh jupyter lab \
			--LabApp.token=$pass

# generate reverse proxy entry
if [ ! -z "$proxy_path" ]
then
	config=$(<config/code.subfolder.conf.sample)
	config="${config/DOMAIN/$domain}"
	config="${config//NAME/$name}"
	config="${config/CONTAINER_PORT/$port}"
	tee ${proxy_path}/${name}.code.subfolder.conf <<< $config
    if [ ! -z "$proxy_container" ]
    then
		docker restart $proxy_container
    fi
fi