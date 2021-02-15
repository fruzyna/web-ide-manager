#!/bin/bash

name=$1
pass=$2
port=$3
volume_name=$4
cpus=${5:-"0.5"}
ram=${6:-"2.0"}
swap=${7:-"5.0"}

container_name=jupyter-${name}

if [ -z "$volume_name" ] || [ "$volume_name" == "-" ]
then
	volume_name=jnb-${name}-vol
	docker volume create $volume_name
fi

# start docker container
docker run -d --name $container_name \
			-e JUPYTER_ENABLE_LAB=yes \
			-p $port:8888 \
		   --cpus $cpus -m ${ram}g --memory-swap ${swap}g \
			-v $volume_name:/home/jovyan \
		   --restart unless-stopped \
			jupyter/datascience-notebook \
			start.sh jupyter lab \
			--LabApp.token=$pass