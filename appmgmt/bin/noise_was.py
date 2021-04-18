# Hacked together by Simon Shelston - simon@splunk.com
#

import datetime,os, random, re

if os.environ["SPLUNK_HOME"].find('\\') == -1:
	theFile = open(os.environ["SPLUNK_HOME"] +  os.path.abspath('/etc/apps/appmgmt/bin/sample/noise_was.sample'), 'r')
else:
	theFile = open(os.environ["SPLUNK_HOME"] +  ('\\etc\\apps\\appmgmt\\bin\\sample\\noise_was.sample'), 'r')

file = theFile.readlines()

loopCount = random.randint(10, 25)

for i in range(1):

	ipAddresses = ["10.2.1.44", "192.1.2.40", "10.2.1.11", "10.2.1.45", "170.192.178.10", "178.19.3.199", "192.0.1.42", "189.222.1.22", "177.23.21.22"]
	ipAddress = ipAddresses[random.randint(0, len(ipAddresses) - 1)]

	serverNames = ["store-adminserver", "store-server1", "store-server2", "store-server3"]
	serverName = serverNames[random.randint(0, len(serverNames) - 1)]

	prevTime = datetime.datetime.utcnow()
	
	for lines in file:
		# Replace stuff
		randSecs = random.randint(0, 3) # Randomize users "think" time	
		time = datetime.datetime.utcnow()
		time = prevTime + datetime.timedelta(seconds=randSecs) # Ensure that the time always goes up
	
		# Don't write any future events past 1 min
		if (time > (datetime.datetime.utcnow() + datetime.timedelta(minutes=1))) & (lines.startswith("[")):
			break
		#[3/16/10 17:25:56:788 CDT]
		line = re.sub('\[\d+/\d+/\d+\s\d+:\d+:\d+:\d+\s\w{3}]', time.strftime('[%m/%d/%y %H:%M:%S UTC]'), lines)
		#line = re.sub('virt4', serverName, line)
		print (line),
		
		prevTime = time

