# Binary mengikuti arsitektur target Docker.
FROM alpine:3.22
ARG PB_VERSION=0.40.5
ARG TARGETARCH
ARG TARGETVARIANT
ARG PB_URL=https://github.com/pocketbase/pocketbase/releases/download

RUN apk add --no-cache ca-certificates wget unzip \
 && case "${TARGETARCH}/${TARGETVARIANT}" in \
      amd64/*) PB_ARCH=amd64 ;; \
      arm64/*) PB_ARCH=arm64 ;; \
      arm/v7) PB_ARCH=armv7 ;; \
      *) echo "Arsitektur tidak didukung: ${TARGETARCH}/${TARGETVARIANT}"; exit 1 ;; \
    esac \
 && PB_ARCHIVE="pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" \
 && cd /tmp \
 && wget -q "${PB_URL}/v${PB_VERSION}/${PB_ARCHIVE}" \
 && wget -q "${PB_URL}/v${PB_VERSION}/checksums.txt" \
 && grep " ${PB_ARCHIVE}$" checksums.txt | sha256sum -c - \
 && unzip "${PB_ARCHIVE}" pocketbase -d /usr/local/bin \
 && rm "${PB_ARCHIVE}" checksums.txt

EXPOSE 8090
CMD ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb_data", "--hooksDir=/pb_hooks"]
