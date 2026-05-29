FROM python:3.12-slim

# pipe'lar yarim-yuklashda fail-closed bo'lsin
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates cron git tar gzip && rm -rf /var/lib/apt/lists/*

# Skanerlar — pinned (reproducible build)
# Trivy: GitHub release tarball + SHA256 integrity tekshiruvi (install.sh redirect
# endpoint eski versiyalarda 404; checksum tasdig'i supply-chain himoyasi uchun shart)
RUN set -eux; cd /tmp; \
    curl -fsSL -O https://github.com/aquasecurity/trivy/releases/download/v0.70.0/trivy_0.70.0_Linux-64bit.tar.gz; \
    curl -fsSL -O https://github.com/aquasecurity/trivy/releases/download/v0.70.0/trivy_0.70.0_checksums.txt; \
    grep ' trivy_0.70.0_Linux-64bit.tar.gz$' trivy_0.70.0_checksums.txt | sha256sum -c -; \
    tar xz -C /usr/local/bin -f trivy_0.70.0_Linux-64bit.tar.gz trivy; \
    rm -f trivy_0.70.0*
# Grype + Syft (anchore install skriptlari GitHub release'dan yuklaydi)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
      | sh -s -- -b /usr/local/bin v0.112.0
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
      | sh -s -- -b /usr/local/bin v1.44.0

WORKDIR /opt/tizim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY crontab /etc/cron.d/tizim
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod 0644 /etc/cron.d/tizim && crontab /etc/cron.d/tizim \
    && chmod +x /docker-entrypoint.sh

# Cron Docker env'ni meros olmaydi → entrypoint env'ni /etc/environment'ga yozadi
CMD ["/docker-entrypoint.sh"]
