FROM python:3.11-bookworm
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
WORKDIR /app
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash coreutils iverilog make \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir cocotb==2.0.0 pytest==8.3.5
RUN mkdir -p /app /logs/verifier
COPY . /tests/
RUN chmod 0755 /tests/test.sh
