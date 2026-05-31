FROM alpine:3.19

# Install recon tools and SSH server
RUN apk add --no-cache \
    curl \
    wget \
    bind-tools \
    netcat-openbsd \
    nmap \
    jq \
    bash \
    openssh \
    && rm -rf /var/cache/apk/*

# Generate host keys for SSH
RUN ssh-keygen -A

# Configure SSH daemon settings to allow password login and TCP tunneling (port forwarding)
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/g' /etc/ssh/sshd_config && \
    sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/g' /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config

# Create a ctf user for players to log into and configure their login shell to our wrapper
COPY ssh-wrapper.sh /usr/local/bin/ssh-wrapper.sh
RUN apk add --no-cache dos2unix && \
    dos2unix /usr/local/bin/ssh-wrapper.sh && \
    chmod +x /usr/local/bin/ssh-wrapper.sh && \
    echo "/usr/local/bin/ssh-wrapper.sh" >> /etc/shells && \
    adduser -D -s /usr/local/bin/ssh-wrapper.sh ctf && \
    echo "ctf:numidian123" | chpasswd

# Drop a welcome message and developer notes
RUN mkdir -p /home/ctf
COPY motd.txt /etc/motd
COPY developer_notes.txt /home/ctf/developer_notes.txt
RUN echo "nmctf{n0t_th4t_e4sy_l0l_k33p_p1v0t1ng}" > /tmp/flag.txt
RUN chown -R ctf:ctf /home/ctf

# Set up a bashrc that applies history protections for interactive sessions
RUN echo 'cat /etc/motd' > /home/ctf/.bashrc && \
    echo 'export PS1="4mdj4d@jumpbox:\\w\\$ "' >> /home/ctf/.bashrc && \
    echo 'export HISTFILE=/dev/null' >> /home/ctf/.bashrc && \
    echo 'export HISTSIZE=0' >> /home/ctf/.bashrc && \
    echo 'export HISTFILESIZE=0' >> /home/ctf/.bashrc && \
    ln -sf /dev/null /home/ctf/.bash_history

# Expose container SSH port
EXPOSE 22

# Start SSH daemon in the foreground and log to stderr
CMD ["/usr/sbin/sshd", "-D", "-e"]
