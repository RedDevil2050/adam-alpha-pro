#!/bin/bash

# Set colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== DOCKER SYSTEM DIAGNOSTICS ===${NC}"

# Check if Docker is running
echo -e "\n${YELLOW}Checking if Docker daemon is running...${NC}"
if systemctl is-active --quiet docker || docker info >/dev/null 2>&1; then
    echo -e "${GREEN}Docker is running.${NC}"
else
    echo -e "${RED}Docker is NOT running! Try starting it with:${NC}"
    echo "systemctl start docker    # For systemd-based systems"
    echo "service docker start      # For init.d-based systems"
    exit 1
fi

# Show Docker info
echo -e "\n${YELLOW}=== Docker System Info ===${NC}"
docker info

# Check disk space
echo -e "\n${YELLOW}=== Disk Space Check ===${NC}"
df -h | grep -E 'Filesystem|/$|/var' 

# Show Docker resource usage
echo -e "\n${YELLOW}=== Docker Resource Usage ===${NC}"
docker system df -v

# List running and stopped containers
echo -e "\n${YELLOW}=== Container Status ===${NC}"
docker ps -a

# Check for containers with restart issues
echo -e "\n${YELLOW}=== Containers with Restart Issues ===${NC}"
docker ps -a | grep -E 'Restarting|unhealthy|Exited \([1-9][0-9]*\)'

# Show last 20 lines of logs for containers with issues
echo -e "\n${YELLOW}=== Logs for Problematic Containers ===${NC}"
for container in $(docker ps -a --format "{{.ID}}" --filter "status=exited" --filter "status=restarting"); do
    container_name=$(docker inspect --format '{{.Name}}' $container | sed 's/^\///')
    echo -e "\n${YELLOW}--- Last 20 logs for $container_name (ID: $container) ---${NC}"
    docker logs --tail 20 $container 2>&1
    
    # Show exit code for stopped containers
    if [[ $(docker inspect --format='{{.State.Status}}' $container) == "exited" ]]; then
        exit_code=$(docker inspect --format='{{.State.ExitCode}}' $container)
        echo -e "${RED}Container exited with code $exit_code${NC}"
        
        # Provide insight based on common exit codes
        case $exit_code in
            125) echo "Error: Docker daemon issue" ;;
            126) echo "Error: Command cannot be invoked" ;;
            127) echo "Error: Command not found" ;;
            137) echo "Error: Container received SIGKILL (likely OOM killed)" ;;
            139) echo "Error: Container received SIGSEGV (segmentation fault)" ;;
            143) echo "Error: Container received SIGTERM" ;;
        esac
    fi
done

# Check Docker networks
echo -e "\n${YELLOW}=== Docker Networks ===${NC}"
docker network ls

# Check for Docker Compose
echo -e "\n${YELLOW}=== Docker Compose Detection ===${NC}"
compose_files=$(find . -maxdepth 2 -name "docker-compose*.yml" -o -name "compose*.yml" 2>/dev/null)
if [ -n "$compose_files" ]; then
    echo -e "Found Docker Compose files:"
    echo "$compose_files"
    
    for file in $compose_files; do
        echo -e "\n${YELLOW}Validating compose file: $file${NC}"
        docker-compose -f $file config
        
        echo -e "\n${YELLOW}Compose services status for $file:${NC}"
        docker-compose -f $file ps
    done
else
    echo "No Docker Compose files found in current directory"
fi

# Check for resource constraints
echo -e "\n${YELLOW}=== System Resource Check ===${NC}"
echo -e "Memory Usage:"
free -h
echo -e "\nCPU Load:"
uptime

# Check common Docker socket issues
echo -e "\n${YELLOW}=== Docker Socket Check ===${NC}"
if [ -S /var/run/docker.sock ]; then
    ls -la /var/run/docker.sock
    echo "Docker socket exists."
    if [ -r /var/run/docker.sock ] && [ -w /var/run/docker.sock ]; then
        echo -e "${GREEN}Current user has proper permissions to Docker socket.${NC}"
    else
        echo -e "${RED}Permission issue with Docker socket. Try:${NC}"
        echo "sudo usermod -aG docker \$USER"
        echo "newgrp docker"
    fi
else
    echo -e "${RED}Docker socket not found at /var/run/docker.sock${NC}"
fi

# Final recommendations
echo -e "\n${YELLOW}=== Troubleshooting Recommendations ===${NC}"
echo "1. For containers with exit codes, check their logs for specific errors"
echo "2. If containers are OOM killed (exit code 137), increase memory limits"
echo "3. Check for port conflicts with: docker port <container_name>"
echo "4. Try restarting the Docker daemon: sudo systemctl restart docker"
echo "5. Consider freeing resources with: docker system prune"
echo "6. Check application logs inside containers: docker exec <container> cat /path/to/logs"

echo -e "\n${YELLOW}=== Diagnostics Complete ===${NC}"
