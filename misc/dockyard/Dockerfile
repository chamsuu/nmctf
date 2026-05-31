# Docker-in-Docker base image to orchestrate the inner challenge containers
FROM docker:24-dind

# Install docker-compose, bash, and socat to route port 22 inside the parent to jumpbox
RUN apk add --no-cache docker-compose bash socat

# Define workspace
WORKDIR /challenge

# Copy all challenge directories and configurations
COPY . .

# Set up the bootstrap shell script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the outer port that CTFd-Whale will connect to for SSH routing
EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
