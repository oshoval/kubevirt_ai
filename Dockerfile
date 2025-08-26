FROM quay.io/fedora/fedora:42

RUN echo '[google-cloud-cli]' > /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'name=Google Cloud CLI' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-x86_64' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'enabled=1' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'gpgcheck=1' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'repo_gpgcheck=0' >> /etc/yum.repos.d/google-cloud-sdk.repo && \
    echo 'gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg' >> /etc/yum.repos.d/google-cloud-sdk.repo

RUN dnf update -y && \
    dnf install -y libxcrypt-compat.x86_64 google-cloud-cli nodejs npm

RUN mkdir -p /root/.npm-global && \
    npm config set prefix '/root/.npm-global' && \
    npm install -g @anthropic-ai/claude-code

ENV PATH="$PATH:/root/.npm-global/bin"
ENV CLAUDE_CODE_USE_VERTEX=1
ENV CLOUD_ML_REGION=us-east5

# Set working directory
WORKDIR /app

# Default command
CMD ["/bin/bash"]
