# dsh-box image: the egress-lab base (Ubuntu 24.04 + build-essential + strace) plus musl-tools,
# so `native/system/scripts/build.ts` builds landlock-run with musl-gcc exactly as upstream does.
# 0.2 (2026-11-17, SAN-4472) adds ripgrep and git: Sando's lean prompt searches with `rg` and the 0.1 box had
# neither, which skewed the head-to-head against it (every t4 run hit `rg: command not found`).
#   docker build -t shrinetech-dsh-box:0.2 shrinetech/box-image
FROM shrineai-egress-lab:0.2
RUN apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends musl-tools ripgrep git \
    && rm -rf /var/lib/apt/lists/*
