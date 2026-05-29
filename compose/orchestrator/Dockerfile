FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates cron git tar gzip && rm -rf /var/lib/apt/lists/*

# Skanerlar — pinned (reproducible build)
# Trivy: to'g'ridan-to'g'ri GitHub release tarball (install.sh redirect endpoint
# eski versiyalar uchun 404 qaytaradi — shuning uchun ishonchli direct download)
RUN curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v0.70.0/trivy_0.70.0_Linux-64bit.tar.gz \
      | tar xz -C /usr/local/bin trivy
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
