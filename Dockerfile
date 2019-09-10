#
# FogLAMP on IOx
# 
FROM ubuntu:18.04

# Must setup timezone or apt-get hangs with prompt
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install packages required for FogLAMP
RUN apt update && \
    apt -y install wget rsyslog python3-dbus iputils-ping sysstat curl && \
    wget --quiet https://s3.amazonaws.com/foglamp/debian/x86_64/foglamp-1.6.0-x86_64_ubuntu_18_04.tgz && \
    tar -xzvf ./foglamp-1.6.0-x86_64_ubuntu_18_04.tgz && \
    # Install dependencies of the base FogLAMP package
    apt -y install `dpkg -I ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-1.6.0-x86_64.deb | awk '/Depends:/{print$2}' | sed 's/,/ /g'` && \
    # Extract files from base FogLAMP package
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-1.6.0-x86_64.deb foglamp-1.6.0-x86_64 && \
    # Extract files for Notification Service
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-service-notification-1.6.0-x86_64.deb foglamp-service-notification-1.6.0-x86_64 && \
    # Notification plugins
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-notify-python35-1.6.0-x86_64_ubuntu_18_04.deb foglamp-notify-python35-1.6.0-x86_64_ubuntu_18_04 && \
    # North
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-north-httpc-1.6.0-x86_64_ubuntu_18_04.deb foglamp-north-httpc-1.6.0-x86_64_ubuntu_18_04 && \
    # South
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-south-sinusoid-1.6.0.deb foglamp-south-sinusoid-1.6.0 && \
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-south-benchmark-1.6.0-x86_64_ubuntu_18_04.deb foglamp-south-benchmark-1.6.0-x86_64_ubuntu_18_04 && \
    dpkg-deb -R ./foglamp-1.6.0-x86_64_ubuntu_18_04/foglamp-south-systeminfo-1.6.0.deb foglamp-south-systeminfo-x86_64_ubuntu_18_04 && \
    # Copy extracted package files to destination directories
    cp -r ./foglamp-1.6.0-x86_64/usr /. && \
    cp -r ./foglamp-service-notification-1.6.0-x86_64/usr /. && \
    cp -r ./foglamp-notify-python35-1.6.0-x86_64_ubuntu_18_04/usr /. && \
    cp -r ./foglamp-north-httpc-1.6.0-x86_64_ubuntu_18_04/usr /. && \
    cp -r ./foglamp-south-sinusoid-1.6.0/usr /. && \
    cp -r ./foglamp-south-benchmark-1.6.0-x86_64_ubuntu_18_04/usr /. && \
    cp -r ./foglamp-south-systeminfo-1.6.0/usr /. && \
    # move blank database to foglamp data directory
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

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/b100
COPY plugins/south/b100 /usr/local/foglamp/python/foglamp/plugins/south/b100

VOLUME /usr/local/foglamp/data

# FogLAMP API port
EXPOSE 8081 1995 502

# start rsyslog, FogLAMP, and tail syslog
CMD ["bash","/usr/local/foglamp/foglamp.sh"]

LABEL maintainer="rob@raesemann.com" \
      author="Rob Raesemann" \
      target="IOx" \
      version="1.6.0" \