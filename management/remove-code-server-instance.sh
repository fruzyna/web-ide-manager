#!/bin/bash

name=$1

proxy_path=$(<config/proxy_path)
proxy_container=$(<config/proxy_container)

container_name=code-server-${name}
volume_name=cs-${name}-vol

docker stop $container_name
docker rm $container_name
docker volume rm $volume_name

if [ ! -z "$proxy_path" ]
then
    rm ${proxy_path}/${name}.code.subfolder.conf
    if [ ! -z "$proxy_container" ]
    then
        docker restart $proxy_container
    fi
fi