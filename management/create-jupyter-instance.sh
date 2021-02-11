#!/bin/bash

name=$1
pass=$2
port=$3

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