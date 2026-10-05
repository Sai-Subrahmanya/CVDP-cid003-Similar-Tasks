FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
WORKDIR /app
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates coreutils curl iverilog make python3 \
 && rm -rf /var/lib/apt/lists/*
COPY workspace/ /app/
