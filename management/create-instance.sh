#!/bin/bash

kind=$1
name=$2
pass=$3
port=$4

proxy_path=$(<config/proxy_path)
domain=$(<config/domain)
proxy_container=$(<config/proxy_container)

# start docker container
management/create-${kind}-instance.sh $2 $3 $4

# generate reverse proxy entry
if [ ! -z "$proxy_path" ]
then
	path="$name/$kind"
	config=$(<config/subfolder.conf.sample)
	config="${config/DOMAIN/$domain}"
	config="${config//NAME/$path}"
	config="${config/CONTAINER_PORT/$port}"
	tee ${proxy_path}/${name}.${kind}.subfolder.conf <<< $config
    if [ ! -z "$proxy_container" ]
    then
		docker restart $proxy_container
    fi
fi