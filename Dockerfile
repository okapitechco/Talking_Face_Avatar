# Base image -> https://github.com/runpod/containers/blob/main/official-templates/base/Dockerfile
# DockerHub -> https://hub.docker.com/r/runpod/base/tags
# ffmpeg - http://ffmpeg.org/download.html
#
# From https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu
#
# https://hub.docker.com/r/jrottenberg/ffmpeg/
#
#
FROM runpod/base:0.6.2-cuda12.2.0 as base

ENV PKG_CONFIG_PATH=/usr/lib/arm-linux-gnueabihf/pkgconfig/:/usr/local/lib/pkgconfig/
# Update base and install build tools
RUN apt-get update
# Install ffmpeg libraries
RUN apt-get install -y yasm pkg-config nasm unzip

RUN wget https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
RUN tar xjf ffmpeg-snapshot.tar.bz2

## x264 http://www.videolan.org/developers/x264.html
RUN \
        DIR=/tmp/x264 && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://download.videolan.org/pub/videolan/x264/snapshots/x264-snapshot-20191217-2245-stable.tar.bz2 | \
        tar -jx --strip-components=1 && \
        ./configure --prefix="/usr/local" --enable-shared --enable-pic --disable-cli && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN cd ./ffmpeg && PKG_CONFIG_PATH=/usr/lib/arm-linux-gnueabihf/pkgconfig/:/usr/local/lib/pkgconfig/ ./configure \
--prefix=/usr/local \
--enable-gpl \
--enable-libx264 \
--enable-nonfree && \
make && \
make install

# --- Optional: System dependencies ---
COPY ./runpod-setup.sh /setup.sh
RUN /bin/bash /setup.sh && \
    rm /setup.sh

# Python dependencies
COPY requirements.txt /requirements.txt
RUN PIP_REQUIRE_HASHES= python3.11 -m pip install --upgrade pip && \
    PIP_REQUIRE_HASHES= python3.11 -m pip install --upgrade -r /requirements.txt --no-cache-dir && \
    rm /requirements.txt
    

ADD . .
# Download models
RUN bash scripts/download_models.sh
RUN cd ./checkpoints && unzip ./BFM_Fitting.zip

# NOTE: The base image comes with multiple Python versions pre-installed.
#       It is reccommended to specify the version of Python when running your code.

# Add src files (Worker Template)

CMD python3.11 -u /runpod_handler.py
