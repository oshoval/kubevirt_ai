FROM quay.io/fedora/fedora:42

RUN echo '[google-cloud-cli]' > /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'name=Google Cloud CLI' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-x86_64' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'enabled=1' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'gpgcheck=1' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'repo_gpgcheck=0' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg' >> /etc/yum.repos.d/google-cloud-sdk.repo

RUN dnf update -y && \
    dnf install -y libxcrypt-compat.x86_64 google-cloud-cli nodejs npm git python make pip

# Install kubectl
RUN curl -LO https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin

# Install Go 1.24
RUN curl -LO https://golang.org/dl/go1.24.0.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz && \
    rm go1.24.0.linux-amd64.tar.gz

RUN mkdir -p /root/.npm-global && \
    npm config set prefix '/root/.npm-global' && \
    npm install -g @anthropic-ai/claude-code

# Clone kubevirt_ai project
RUN mkdir -p /root/project && \
    cd /root/project && \
    git clone https://github.com/oshoval/kubevirt_ai.git && \
    cd kubevirt_ai && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt && \
    PATH=$PATH:/usr/local/go/bin make build && \
    mkdir -p /root/project/kubevirt_ai/kubevirt_ai_agent_logs

ENV PATH="$PATH:/root/.npm-global/bin:/usr/local/go/bin"
ENV GOPATH="/root/go"
ENV GOROOT="/usr/local/go"
ENV CLAUDE_CODE_USE_VERTEX=1
ENV CLOUD_ML_REGION=us-east5

# Set working directory
WORKDIR /root/project/kubevirt_ai

# Default command
CMD ["/bin/bash"]
