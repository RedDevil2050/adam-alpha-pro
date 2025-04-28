#!/bin/bash

echo "=== Docker System Info ==="
docker info

echo -e "\n=== Docker Containers Status ==="
docker ps -a

echo -e "\n=== Docker Images ==="
docker images

echo -e "\n=== Disk Space ==="
df -h

echo -e "\n=== Docker Volume Usage ==="
docker system df -v

echo -e "\n=== Docker Network Status ==="
docker network ls

# Get logs for all containers
echo -e "\n=== Container Logs ==="
for container in $(docker ps -a --format "{{.Names}}"); do
  echo -e "\n--- Logs for $container ---"
  docker logs --tail 30 $container 2>&1
done
