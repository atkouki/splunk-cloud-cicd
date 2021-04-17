# SPLUNK Cloud and CI/CD

## How to use this repository :

### Prerequisite 
* Use this [Tutorial](https://embeddedinventor.com/complete-guide-to-setting-up-gitlab-locally-on-mac/) to create a GITLAB server and a GITLab Runner
* Install AppInspect and docker on your GitLab Runner
* Add the GitLab Runner Ip adress to your splunk cloud white list 
* create an index named `appmgmt`
* Create an empty application named `testing_app`

### Repo Content :
* `.gitlab-ci.yml` : define all CI/CD tasks
* `appmgmt` : Application generating noise ; used to generate events and validate fields extraction and parsing.
* `docker_validation.sh` : script used to validate app installation , fields extractions ... create a docker , install Splunk, install the appmgmt app to generate noise, install the targeted application and run some tests to validate fields extraction.
* `python_scripts` : contains python scripts used to deploy configurations and dashboards (`for the POC, the splunk cloud url, login and password are not encrypted -> need to be changed for obvious security reasons`)
* `testing_app` : the application that will be validated, tested and deployed 
* `versions` : 2 different definitions of the custom_access_combined sourcetype and a testing dashboard 

### CI/CD Tasks :
All those tasks are defined in the .gitlab-ci.yml file :
* `validate-app` : call splunk-appinspect to validate the app structure ...
* `generate-data` : will run the cicd_runner.sh to validate fields extraction
* `deploy-configs` : Run the python scripts to deploy all configurations and dashboards using splunk cloud endpoints


# Limitations
* At this step only configuration files and dashboards/views can be managed in a CICD pipline (no scripts, no file based lookups, no resources:pictures, .css, .. )
