ARG network_mode=default

FROM python:3.13-slim AS builder-proxy
COPY /cacert.pem /cacert.pem

FROM python:3.13-slim AS builder-default

FROM builder-${network_mode} AS builder
WORKDIR /app

COPY pyproject.toml ./
COPY . .

RUN if [ -f /cacert.pem ]; then \
      REQUESTS_CA_BUNDLE=/cacert.pem PIP_CERT=/cacert.pem CURL_CA_BUNDLE=/cacert.pem pip install .[dev]; \
    else \
      pip install .[dev]; \
    fi
    
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
