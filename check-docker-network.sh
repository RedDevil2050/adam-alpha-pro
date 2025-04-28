#!/bin/bash

echo "=== Docker Networks ==="
docker network ls

echo -e "\n=== Detailed Network Inspection ==="
for network in $(docker network ls --format "{{.Name}}"); do
  echo -e "\n--- Network: $network ---"
  docker network inspect $network
done

echo -e "\n=== Container Network Settings ==="
for container in $(docker ps -q); do
  echo -e "\n--- Container: $(docker inspect --format '{{.Name}}' $container) ---"
  docker inspect --format '{{json .NetworkSettings}}' $container | jq
done
