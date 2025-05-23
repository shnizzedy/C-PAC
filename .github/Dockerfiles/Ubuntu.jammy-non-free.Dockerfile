# Copyright (C) 2023  C-PAC Developers

# This file is part of C-PAC.

# C-PAC is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# C-PAC is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with C-PAC. If not, see <https://www.gnu.org/licenses/>.
FROM ghcr.io/fcp-indi/c-pac_templates:latest as c-pac_templates
FROM neurodebian:jammy-non-free AS dcan-hcp

ARG DEBIAN_FRONTEND=noninteractive
# add DCAN dependencies & HCP code
RUN apt-get update \
    && apt-get install -y git \
    && mkdir -p /opt/dcan-tools \
    && git clone -b 'v2.0.0' --single-branch --depth 1 https://github.com/DCAN-Labs/DCAN-HCP.git /opt/dcan-tools/pipeline

# use neurodebian runtime as parent image
FROM neurodebian:jammy-non-free
LABEL org.opencontainers.image.description="NOT INTENDED FOR USE OTHER THAN AS A STAGE IMAGE IN A MULTI-STAGE BUILD \
Ubuntu Jammy base image"
LABEL org.opencontainers.image.source=https://github.com/FCP-INDI/C-PAC
ARG BIDS_VALIDATOR_VERSION=1.14.6 \
    DEBIAN_FRONTEND=noninteractive
ENV TZ=America/New_York \
    PATH=$PATH:/.local/bin \
    PYTHONPATH=$PYTHONPATH:/.local/lib/python3.10/site-packages

# add default user
RUN groupadd -r c-pac \
    && useradd -r -g c-pac c-pac_user \
    && mkdir -p /home/c-pac_user/ \
    && chown -R c-pac_user:c-pac /home/c-pac_user \
    && chmod 777 / /home/c-pac_user /opt \
    && chmod ugo+w /etc/passwd \
    && chmod a+s /opt \
    # set up for noninteractive apt
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      apt-utils \
      apt-transport-https \
      build-essential \
      ca-certificates \
      curl \
      dc \
      gnupg \
      graphviz \
      graphviz-dev \
      locales \
      rdfind \
      xvfb \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG="en_US.UTF-8" \
    # # install bids-validator
    && curl -fsSL https://raw.githubusercontent.com/tj/n/master/bin/n | bash -s lts \
    && npm install -g "bids-validator@${BIDS_VALIDATOR_VERSION}"

COPY --from=c-pac_templates /cpac_templates /cpac_templates
COPY --from=dcan-hcp /opt/dcan-tools/pipeline/global /opt/dcan-tools/pipeline/global
COPY --from=ghcr.io/fcp-indi/c-pac/neuroparc:v1.0-human /ndmg_atlases /ndmg_atlases

# Installing surface files for downsampling
COPY --from=c-pac_templates /opt/dcan-tools/pipeline/global/templates/standard_mesh_atlases/ /opt/dcan-tools/pipeline/global/templates/standard_mesh_atlases/
COPY --from=c-pac_templates /opt/dcan-tools/pipeline/global/templates/Greyordinates/ /opt/dcan-tools/pipeline/global/templates/Greyordinates/

ENTRYPOINT ["/bin/bash"]

# Link libraries for Singularity images
RUN ldconfig \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip/*

# Set user
USER c-pac_user
