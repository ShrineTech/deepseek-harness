# dsh-box image: the egress-lab base (Ubuntu 24.04 + build-essential + strace) plus musl-tools,
# so `native/system/scripts/build.ts` builds landlock-run with musl-gcc exactly as upstream does.
#   docker build -t shrinetech-dsh-box:0.1 shrinetech/box-image
FROM shrineai-egress-lab:0.2
RUN apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends musl-tools \
    && rm -rf /var/lib/apt/lists/*
