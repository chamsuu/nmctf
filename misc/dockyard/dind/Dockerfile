FROM docker:24-dind

# Copy the initialization script to seed nested containers
COPY init-dind.sh /usr/local/bin/init-dind.sh
RUN chmod +x /usr/local/bin/init-dind.sh

# Wrap the default entrypoint to spawn our init script in the background and run dockerd strictly on the Unix socket
ENTRYPOINT ["sh", "-c", "/usr/local/bin/init-dind.sh & exec dockerd --host=unix:///var/run/docker.sock"]
