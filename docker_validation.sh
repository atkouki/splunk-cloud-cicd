#!/bin/bash


#set -x

if [ $# -lt 1 ]; then
      echo "Usage: cicd_runner.sh <splunk_8_0_1>"
      exit 1
fi

version=$1
APP_ROOT=$2
APP_SAMPLE="appmgmt"
APPS_DIR="/opt/splunk/etc/apps"
USER="admin"
PASSWORD="newPassword"
REGISTRY="weberjas"
CI_PROJECT_DIR=${CI_PROJECT_DIR:-`pwd`}

echo "Running image: ${version}..."

# The Docker network allows the Splunk and testing containers to communicate
echo "Create a bridge network for the containers to communicate"
docker network create testingnet

# Create the Splunk container from the image but do not start it yet
echo "Starting splunk image $version:latest..."
#docker container create --name $version --hostname "idx-example.splunkcloud.com" --network testingnet $REGISTRY/$version:latest
echo "docker container create --rm --name $version --hostname 'idx-example.splunkcloud.com' --network testingnet $REGISTRY/$version:latest"
docker container create --rm --name $version --hostname "idx-example.splunkcloud.com" --network testingnet -e SPLUNK_LICENSE_URI=Free $REGISTRY/$version:latest

# Copy app and configuration into Splunk container
echo "==========================================="
echo "Copying data into container..."
echo "==========================================="

echo "docker cp $CI_PROJECT_DIR/$APP_ROOT $version:$APPS_DIR/"
docker cp $CI_PROJECT_DIR/$APP_ROOT $version:$APPS_DIR/
cho "docker cp $CI_PROJECT_DIR/$APP_SAMPLE $version:$APPS_DIR/"
docker cp $CI_PROJECT_DIR/$APP_SAMPLE $version:$APPS_DIR/
echo "docker cp $CI_PROJECT_DIR/output $version:/"
docker cp $CI_PROJECT_DIR/output $version:/

echo "docker cp $CI_PROJECT_DIR/Splunk_Enterprise_NFR_Q1FY22.lic $version:/tmp/"
docker cp $CI_PROJECT_DIR/Splunk_Enterprise_NFR_Q1FY22.lic $version:/tmp/


# Start Splunk container
echo "==========================================="
echo "starting ${version}..."
echo "==========================================="
docker start $version

# Update Splunk license
echo "==========================================="
echo "Update splunk License ..."
echo "==========================================="
docker exec $version bash -c "/opt/splunk/bin/splunk add licenses /tmp/Splunk_Enterprise_NFR_Q1FY22.lic"
 
# Start Splunk container
echo "==========================================="
echo "restarting splunk ..."
echo "==========================================="
docker exec $version bash -c "/opt/splunk/bin/splunk restart"

# Wait for instance to be available
# Waiting for 2 and a half minutes.
loopCounter=30
mainReady=0
# forwarderReady=0
echo "Wait for Splunk to be available..."

while [[ $loopCounter != 0 && $mainReady != 1 ]]; do
  ((loopCounter--))
  health=`docker ps --filter "name=${version}" --format "{{.Status}}"`

# TODO document the container status
# health will be one of these values: 
  if [[ ! $health =~ "starting" ]]; then
    echo "container running, checking data status..."
    eventCount=`docker exec $version bash -c "SPLUNK_USERNAME=admin SPLUNK_PASSWORD=newPassword /opt/splunk/bin/splunk search 'index=appmgmt sourcetype=custom_access_combined | stats count' -app testing_app"`
    # This count reflects the number of events which are read from the
    # test data file.
    
    eventCount=`echo $eventCount | sed 's/[^0-9]*//g'`

    if [[ $eventCount -gt 0 ]]; then
      echo "Data full indexed! Generated Count : ${eventCount}"
      mainReady=1
    fi
  fi

 # if the container is no longer running...
  if [[ $health == "" ]]; then
    echo "Health:\n${health}\n"
    echo "--------------------------------"
    docker ps -a
    echo "--------------------------------"
    docker inspect $version
    echo "--------------------------------"
    docker logs $version
    echo "--------------------------------"
    echo "Container is no longer running!"
    exit 1
  fi

  echo "loopCounter: ${loopCounter}"
  echo "mainReady: ${mainReady}"
  sleep 5
done

if [[ $mainReady != 1 ]]; then
  echo "Timeout waiting for data to be ingested into Splunk!"
  docker exec $version bash -c "ls -l /output"
  docker logs $version
  exit 1
fi

echo "==========================================="
echo "Setting up test environment..."
echo "==========================================="

# Prevent splunk from prompting for password reset
docker exec $version bash -c "touch /opt/splunk/etc/.ui_login"
# Run btool on the Splunk container
# TODO: Will this create a failure state if there is something wrong with btool or will it just report the error and move on?
docker exec $version bash -c "/opt/splunk/bin/splunk btool check --debug"

echo "-------------------------------------"


# Run saved searches
echo "Running Searches to check fields extractions..."

fieldsCount=`docker exec $version bash -c "SPLUNK_USERNAME=admin SPLUNK_PASSWORD=newPassword /opt/splunk/bin/splunk search 'index=appmgmt sourcetype=custom_access_combined clientip=* ident=* user=* req_time=* method=* uri_path=* bytes=* referer=* useragent=* coockie=* fake=* | head 1000 | stats count' -app testing_app"`
# This count reflects the number of events that contains mandatory fields.

fieldsCount=`echo $fieldsCount | sed 's/[^0-9]*//g'`

if [[ $fieldsCount = 0 ]]; then
  echo "Fields extractions : KO : ${fieldsCount}"
  exit 1
fi

echo "Fields extractions : OK : ${fieldsCount}"

echo "-------------------------------------"