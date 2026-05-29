FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates cron git && rm -rf /var/lib/apt/lists/*

# Skanerlar — barchasi pinned (reproducible build)
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
      | sh -s -- -b /usr/local/bin v0.56.2
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
