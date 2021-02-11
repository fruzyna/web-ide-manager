#!/bin/bash

kind=$1
name=$2

proxy_path=$(<config/proxy_path)
proxy_container=$(<config/proxy_container)

if [[ "$kind" == "code-server" ]]
then
    container_name=code-server-${name}
    volume_name=cs-${name}-vol
elif [[ "$kind" == "jupyter" ]]
then
    container_name=jupyter-${name}
    volume_name=jnb-${name}-vol
elif [[ "$kind" == "frc-java" ]]
then
    container_name=frc-java-${name}
    volume_name=frc-${name}-vol
fi

docker stop $container_name
docker rm $container_name
docker volume rm $volume_name

if [ ! -z "$proxy_path" ]
then
    rm ${proxy_path}/${name}.${kind}.subfolder.conf
    if [ ! -z "$proxy_container" ]
    then
        docker restart $proxy_container
    fi
fi