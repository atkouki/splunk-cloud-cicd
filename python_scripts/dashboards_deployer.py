import os
import requests
import json
import subprocess
import shlex
import sys

print ' === Argument List: ', str(sys.argv)

directory = os.path.join(sys.argv[2], sys.argv[3], "default", "data", "ui", "views") 
appname = sys.argv[3]
server_url = sys.argv[1]


for filename in os.listdir(directory):
    if filename.endswith(".xml") :
        print "#######################################################################\n"
        print("###     Processing dashboard : {}".format(filename))
        print "#######################################################################\n\n\n"
        dashboard_file_name = filename.replace(".xml","")


        dash = open(os.path.join(directory, filename), 'r') 
        content = dash.read()
        
        request_url = server_url + '/servicesNS/nobody/'+appname+'/data/ui/views'
        print("   |__ request URL : "+ request_url + "\n\n")
        data = { 'name' : dashboard_file_name , 'eai:data': content }

        print "   |__ Request data :"
        print(json.dumps(data))
        print("\n")
        response = requests.post(request_url, data=data, verify=False, auth=('whisper-qa', 'whisper913'))
        print ("   |__  Request response :" + response.content + "\n\n")

        if '<msg type="ERROR">An object with name=' in response.content :
            print ("   |__  dashboard file already exists, update its definition definition!")
            request_url = server_url + '/servicesNS/nobody/'+appname+'/data/ui/views/'+ dashboard_file_name
            data = { 'eai:data': content }
            print "   |__ Request data :"
            print(json.dumps(data))
            print("\n")
            response = requests.post(request_url, data=data, verify=False, auth=('whisper-qa', 'whisper913'))
            print ("   |__  Request response :" + response.content + "\n\n")
        
        if '<msg type="ERROR">Action forbidden.</msg>' in response.content :
            print "Action forbidden , this is probably due to missing application target in your deployment server"
            exit(1)
        
        continue
    else:
        continue

# Submit navigation conf

directory = os.path.join(sys.argv[2], sys.argv[3], "default", "data", "ui", "nav") 

for filename in os.listdir(directory):
    if filename.endswith(".xml") :
        print "#######################################################################\n"
        print("###     Processing nav file : {}".format(filename))
        print "#######################################################################\n\n\n"
        nav_file_name = filename.replace(".xml","")


        nav = open(os.path.join(directory, filename), 'r') 
        content = nav.read()
        
        request_url = server_url + '/servicesNS/nobody/'+appname+'/data/ui/nav'
        print("   |__ request URL : "+ request_url + "\n\n")
        data = { 'name' : nav_file_name , 'eai:data': content }

        print "   |__ Request data :"
        print(json.dumps(data))
        print("\n")
        response = requests.post(request_url, data=data, verify=False, auth=('whisper-qa', 'whisper913'))
        print ("   |__  Request response :" + response.content + "\n\n")
        if '<msg type="ERROR">An object with name=' in response.content :
            print ("   |__  nav file already exists, update its definition definition!")
            request_url = server_url + '/servicesNS/nobody/'+appname+'/data/ui/nav/'+ nav_file_name
            data = { 'eai:data': content }
            print "   |__ Request data :"
            print(json.dumps(data))
            print("\n")
            response = requests.post(request_url, data=data, verify=False, auth=('whisper-qa', 'whisper913'))
            print ("   |__  Request response :" + response.content + "\n\n")


        if '<msg type="ERROR">Action forbidden.</msg>' in response.content :
            print "Action forbidden , this is probably due to missing application target in your deployment server"
            exit(1)

        continue
    else:
        continue 