#!/bin/bash

name=$1
pass=$2
port=$3

sudo=$(<config/sudo_password)

container_name=frc-java-${name}
volume_name=frc-${name}-vol

# TODO create volume of limited size, without overwriting contents of /config
docker volume create $volume_name

# start docker container
docker run -d --name $container_name \
		   -e PUID=1000 -e PGID=1000 -e TZ=America/Chicago \
		   -e PASSWORD=$2 -e SUDO_PASSWORD=$sudo \
		   -p $port:8443 \
		   --cpus 0.5 -m 2.0g --memory-swap 5g \
		   -v $volume_name:/config \
		   --restart unless-stopped \
		   mail929/code-server-frc-java