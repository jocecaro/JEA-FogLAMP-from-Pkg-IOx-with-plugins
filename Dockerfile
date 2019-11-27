#
# FogLAMP on IOx
# 
FROM ubuntu:18.04

# Must setup timezone or apt-get hangs with prompt
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install packages required for FogLAMP
RUN apt update 
RUN apt -y install wget rsyslog python3-dbus iputils-ping sysstat curl libmodbus-dev
RUN wget https://foglamp.s3.amazonaws.com/1.7.0/ubuntu1804/x86_64/foglamp-1.7.0_x86_64_ubuntu1804.tgz && \
    tar -xzvf ./foglamp-1.7.0_x86_64_ubuntu1804.tgz
    # Install dependencies of the base FogLAMP package
RUN apt -y install `dpkg -I ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-1.7.0-x86_64.deb | awk '/Depends:/{print$2}' | sed 's/,/ /g'` 
    # Extract files from base FogLAMP package
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-1.7.0-x86_64.deb foglamp-1.7.0-x86_64
    # Extract files for Notification Service
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-service-notification-1.7.0-x86_64.deb foglamp-service-notification-1.7.0-x86_64 
    # Notification plugins
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-notify-python35-1.7.0-x86_64.deb foglamp-notify-python35-1.7.0-x86_64 
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-notify-email-1.7.0-x86_64.deb foglamp-notify-email-1.7.0-x86_64 
    # Rule plugins
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-rule-simple-expression-1.7.0-x86_64.deb foglamp-rule-simple-expression-1.7.0-x86_64 
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-rule-outofbound-1.7.0-x86_64.deb foglamp-rule-outofbound-1.7.0-x86_64 
    # North
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-north-httpc-1.7.0-x86_64.deb foglamp-north-httpc-1.7.0-x86_64 
    # South
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-south-modbus-1.7.0-x86_64.deb foglamp-south-modbus-1.7.0-x86_64
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-south-sinusoid-1.7.0-x86_64.deb foglamp-south-sinusoid-1.7.0-x86_64
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-south-benchmark-1.7.0-x86_64.deb foglamp-south-benchmark-1.7.0-x86_64 
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-south-systeminfo-1.7.0-x86_64.deb foglamp-south-systeminfo-1.7.0-x86_64 
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-south-flirax8-1.7.0-x86_64.deb foglamp-south-flirax8-1.7.0-x86_64 
RUN dpkg-deb -R ./foglamp/1.7.0/ubuntu1804/x86_64/foglamp-filter-flirvalidity-1.7.0-x86_64.deb foglamp-filter-flirvalidity-1.7.0-x86_64 
    # Copy extracted package files to destination directories
RUN cp -r ./foglamp-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-service-notification-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-rule-simple-expression-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-rule-outofbound-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-notify-python35-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-notify-email-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-north-httpc-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-south-modbus-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-south-sinusoid-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-south-benchmark-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-south-systeminfo-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-south-flirax8-1.7.0-x86_64/usr /. 
RUN cp -r ./foglamp-filter-flirvalidity-1.7.0-x86_64/usr /.
    # move blank database to foglamp data directory
RUN mv /usr/local/foglamp/data.new /usr/local/foglamp/data && \
    cd /usr/local/foglamp && \
    ./scripts/certificates foglamp 365 && \
    chown -R root:root /usr/local/foglamp && \
    chown -R ${SUDO_USER}:${SUDO_USER} /usr/local/foglamp/data 
RUN pip3 install -r /usr/local/foglamp/python/requirements.txt 
RUN apt clean  
    #rm -rf /var/lib/apt/lists/* /foglamp* /usr/include/boost

ENV FOGLAMP_ROOT=/usr/local/foglamp 

WORKDIR /usr/local/foglamp
COPY foglamp.sh foglamp.sh
RUN chown root:root /usr/local/foglamp/foglamp.sh \
    && chmod 777 /usr/local/foglamp/foglamp.sh

RUN pip3 install pymodbus kafka-python asyncio

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/b100
COPY plugins/south/b100 /usr/local/foglamp/python/foglamp/plugins/south/b100

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/selrtac
COPY plugins/south/selrtac /usr/local/foglamp/python/foglamp/plugins/south/selrtac

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/north/kafka_north
COPY plugins/north/kafka_north /usr/local/foglamp/python/foglamp/plugins/north/kafka_north

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/north/http_north
COPY plugins/north/http_north /usr/local/foglamp/python/foglamp/plugins/north/http_north

# Copy certs used by Kafka plugin
RUN mkdir -p /etc/ssl/certs
COPY jea-certs /etc/ssl/certs

VOLUME /usr/local/foglamp/data

# FogLAMP API port
EXPOSE 8081 1995 502 23

# start rsyslog, FogLAMP, and tail syslog
CMD ["bash","/usr/local/foglamp/foglamp.sh"]

LABEL maintainer="rob@raesemann.com" \
      author="Rob Raesemann" \
      target="IOx" \
      version="1.7.0" \
