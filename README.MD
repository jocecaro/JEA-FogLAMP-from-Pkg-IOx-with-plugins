
# JEA FogLAMP Docker IOx Image with B100 South Plugin

This git repository contains Dianomic FogLAMP along with the HTTP North Plugin to allow it to forward data to the aggregator node and the Dynamic Ratings Model B100 Electronic Temperature Monitor for Transformers.

Documentation for Dianomic FogLAMP is available at: 
https://foglamp.readthedocs.io/en/master/

The Dynamic Ratings B100 documentation may be found here:
https://www.dynamicratings.com/b100/

This repository contains the package.yaml file required to create a package file for Cisco IOX v1.8+, but the Docker image itself can run on any platform supporting Docker.

The Docker image is created from the available FogLAMP Debian install packages and produces a Docker image that is less than 250MB.


# To build and test for IOx
You must obtain the appropriate Cisco ioxclient program for the version of IOX being used on the switch. The application is available for Windows, Linux, and MacOS.

#### Reset the ioxclient profile
```
ioxclient profiles -reset
```


#### Build the Docker Image

```
docker build --rm -f "Dockerfile" -t jea-foglamp-iox:latest .
```

#### Save the Docker image to rootfs.tar so that ioxclient can package

```
docker save -o IOx/rootfs.tar jea-foglamp-iox:latest
```

#### Build the package

Windows
```
ioxclient pkg IOx\.
```

Linux and MacOS
```
./ioxclient pkg IOx/.
```

#### Upload the package from the command line

```
ioxclient app install foglamp IOx/package.tar
```
You may also use the Cisco IOx web interface on the Cisco device to upload the package.

# Troublshooting

### Test the FogLAMP API to see if FogLAMP successfully started in the container. If teting locally you can use localhost instead of the container ip.

```
http://<ip of container>:8081/foglamp/ping
```

## To connect to docker image in IOx
ssh into switch

```
enable
```

Run this command from inside switch console. Assumes you named the app package "fogamp", otherwise change name.
```
app-hosting connect appid foglamp session
```

From inside the console, you can see FogLAMP files in /usr/local/foglamp.

The ping command is available to test network connectivity to devices.


## To test locally

The beauty of building the FogLAMP package in Docker is that you can test the image locally prior to deploying to IOx. 

#### Create the volume for FogLAMP data
You only need to do this once unless you are upgrading to a new version of FogLAMP or making major changes. If so, delete the Docker volume and then recreate it.

```
docker create -v /usr/local/foglamp/data --name foglamp-data jea-foglamp-iox:latest /bin/true
```

#### Run interactively

For initial testing, you can run the Docker container interactively. 
```
docker run --volumes-from foglamp-data -it -p 8081:8081 -p 80:80 -p 1995:1995 jea-foglamp-iox:latest /bin/bash
```

If you don't see a series of syslog type messages like shown below, you  need to start foglamp manually.
```
May 24 12:10:13 00cd05c96c62 FogLAMP[211] INFO: server: foglamp.services.core.server: Services monitoring started ...
May 24 12:10:13 00cd05c96c62 FogLAMP[211] INFO: server: foglamp.services.core.server: Announce management API service
```

You can check the foglamp status
```
cd /usr/local/foglamp/bin
./foglamp status
```

To start foglamp, just use the startup script which will start the required
rsyslog daemon and display tail the syslog
```
/usr/local/foglamp/foglamp.sh
```

#### Run detached with autorestart


```
docker run --volumes-from foglamp-data -d -p 8081:8081 -p 80:80 -p 1995:1995 jea-foglamp-iox:latest
```



#### Attach interactively to detached session
```
docker exec -it jea-foglamp-iox:latest /bin/bash 
```
#### View logs
```
docker exec logs jea-foglamp-iox:latest
```
