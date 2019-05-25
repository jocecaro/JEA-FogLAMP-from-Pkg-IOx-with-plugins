#
# FogLAMP on IOx
# 
FROM ubuntu:16.04

# Must setup timezone or apt-get hangs with prompt
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install packages required for FogLAMP
RUN apt update && \
    apt -y install wget rsyslog python3-dbus iputils-ping && \
    wget --quiet https://s3.amazonaws.com/foglamp/debian/x86_64/foglamp-1.5.2-x86_64_ubuntu_16_04.tgz && \
    tar -xzvf ./foglamp-1.5.2-x86_64_ubuntu_16_04.tgz && \
    apt -y install `dpkg -I ./foglamp-1.5.2-x86_64_ubuntu_16_04/foglamp-1.5.2-x86_64.deb | awk '/Depends:/{print$2}' | sed 's/,/ /g'` && \
    dpkg-deb -R ./foglamp-1.5.2-x86_64_ubuntu_16_04/foglamp-1.5.2-x86_64.deb foglamp-1.5.2-x86_64 && \
    dpkg-deb -R ./foglamp-1.5.2-x86_64_ubuntu_16_04/foglamp-south-sinusoid-1.5.2.deb foglamp-south-sinusoid-1.5.2 && \
    cp -r ./foglamp-1.5.2-x86_64/usr /. && \
    cp -r ./foglamp-south-sinusoid-1.5.2/usr /. && \
    mv /usr/local/foglamp/data.new /usr/local/foglamp/data && \
    cd /usr/local/foglamp && \
    ./scripts/certificates foglamp 365 && \
    chown -R root:root /usr/local/foglamp && \
    chown -R ${SUDO_USER}:${SUDO_USER} /usr/local/foglamp/data && \
    pip3 install -r /usr/local/foglamp/python/requirements.txt && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* /foglamp* /usr/include/boost

ENV FOGLAMP_ROOT=/usr/local/foglamp 

WORKDIR /usr/local/foglamp
COPY foglamp.sh foglamp.sh
RUN chown root:root /usr/local/foglamp/foglamp.sh \
    && chmod 777 /usr/local/foglamp/foglamp.sh

RUN pip3 install pymodbus

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/north/http_north
COPY plugins/north/http_north /usr/local/foglamp/python/foglamp/plugins/north/http_north

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/b100
COPY plugins/south/b100 /usr/local/foglamp/python/foglamp/plugins/south/b100

RUN mkdir -p /usr/local/foglamp/plugins/south/random
COPY plugins/south/random /usr/local/foglamp/plugins/south/random

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/systeminfo
COPY plugins/south/systeminfo /usr/local/foglamp/python/foglamp/plugins/south/systeminfo

VOLUME /usr/local/foglamp/data

# FogLAMP API port
EXPOSE 8081 1995 502

# start rsyslog, FogLAMP, and tail syslog
CMD ["bash","/usr/local/foglamp/foglamp.sh"]

LABEL maintainer="rob@raesemann.com" \
      author="Rob Raesemann" \
      target="IOx" \
      version="1.8" \