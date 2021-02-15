#!/bin/bash

name=$1
pass=$2
port=$3
volume_name=$4
cpus=${5:-"0.5"}
ram=${6:-"2.0"}
swap=${7:-"5.0"}

sudo=$(<config/sudo_password)

container_name=frc-java-${name}

if [ -z "$volume_name" ] || [ "$volume_name" == "-" ]
then
	volume_name=frc-${name}-vol
	docker volume create $volume_name
fi

# start docker container
docker run -d --name $container_name \
		   -e PUID=1000 -e PGID=1000 -e TZ=America/Chicago \
		   -e PASSWORD=$2 -e SUDO_PASSWORD=$sudo \
		   -p $port:8443 \
		   --cpus $cpus -m ${ram}g --memory-swap ${swap}g \
		   -v $volume_name:/config \
		   --restart unless-stopped \
		   mail929/code-server-frc-java