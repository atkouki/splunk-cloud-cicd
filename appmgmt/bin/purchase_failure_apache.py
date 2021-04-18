# Hacked together by Simon Shelston - simon@splunk.com
#
# ___ NOTES ___
# Use --debug switch to run in debug mode which will write to stdout and not to file
# Use an integer as a switch to have the script support multiple instances of itself. Make sure to have 
# the monitor:// stanza changed to the _n log name!
#

import time, datetime, os, sys, random

filename = "purchase_failure_apache.log"
debug = False

# Check for arguments
for arg in sys.argv:
	if (arg == "--debug"):
		debug = True

	if (arg.isdigit()):
		filename = str.replace(filename, ".log", "_" + str(arg) + ".log")

# Kill file if it exists.
if(debug == False):
	if os.environ["SPLUNK_HOME"].find('\\') == -1:
		theFile = open(os.environ["SPLUNK_HOME"] +  os.path.abspath('/etc/apps/appmgmt/bin/output/' + filename), 'w')
	else:
		theFile = open(os.environ["SPLUNK_HOME"] +  ('\\etc\\apps\\appmgmt\\bin\\output\\' + filename), 'w')

# Neverending Loop
#loop = 1

#while loop :
	
	# Append to file
	if os.environ["SPLUNK_HOME"].find('\\') == -1:
		theFile = open(os.environ["SPLUNK_HOME"] +  os.path.abspath('/etc/apps/appmgmt/bin/output/' + filename), 'a')
	else:
		theFile = open(os.environ["SPLUNK_HOME"] +  ('\\etc\\apps\\appmgmt\\bin\\output\\' + filename), 'a')
	
	# Define Data
	#############
	
	currentTime = datetime.datetime.utcnow()
	baseUrl = "http://www.buttercupenterprises.com"
	
	# Client IP Addresses
	clientipAddresses = ["10.2.1.44"]
	clientipAddress = clientipAddresses[random.randint(0, len(clientipAddresses) - 1)]

	# Product Ids
#	productIds = ["AV-SB-02", "AV-CB-01","FL-DSH-01","K9-BD-01","K9-CW-01","FL-DLH-02","FI-FW-02","RP-SN-01","FI-SW-01","RP-LI-02"]
	productIds = ["BS-2","MCB-5","MCB-6","MCF-3","ZSG-2","CM-1","DFS-2","PP-5","BW-3","WPSS-2"]
	productId = productIds[random.randint(0, len(productIds) - 1)]

	# Item Ids
	itemIds = ["EST-19","EST-18","EST-14","EST-6","EST-26","EST-17","EST-16","EST-15","EST-27","EST-7","EST-21","EST-11","EST-12","EST-13","EST-20","EST-1"]
	itemId = itemIds[random.randint(0, len(itemIds) - 1)]

	# Category Ids
#	catIds = ["BOUQUETS","GIFTS","FLOWERS","SURPRISE","TEDDY"]
#	catIds = ["Clothing","Books","Gifts"]
#	catId = catIds[random.randint(0, len(catIds) - 1)]

	# JSESSION Ids
	jsessionId = "SD" + str(random.randint(1, 10)) + "SL" + str(random.randint(1, 10)) + "FF" + str(random.randint(1, 10)) + "ADFF" + str(random.randint(1, 10))
	
	# Actions
	actions = ["purchase"]
	action = actions[random.randint(0, len(actions) - 1)]
	
	# Status
	statuses = ["503"]
	status = statuses[random.randint(0, len(statuses) - 1)]
	
	# Method
	methods = ["GET"]
	method = methods[random.randint(0, len(methods) - 1)]
	
	# Bytes Transferred
	bytesXferred = str(random.randint(200,4000))
	
	# Time Taken
	timeTaken =  str(random.randint(100,1000))
	
	uris = [
	"/cart.do?action=" + action + "&itemId=" + itemId + "&product_id=" + productId
	]
	uri = uris[random.randint(0, len(uris) - 1)] + "&JSESSIONID=" + jsessionId
	referralUri = baseUrl + uris[random.randint(0, len(uris) - 1)]
	
	useragents = [
	"Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5 Build/MRA58N) AppleWebKit/537.36(KHTML, like Gecko) Chrome/52.0.2743.8 Mobile Safari/537.36",
"Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; Googlebot/2.1; http://www.google.com/bot.html)",
"Mozilla/5.0 (Linux; Android 7.1.0; Pixel XL Build/NMF26O) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.90 Mobile Safari/537.36",
"Mozilla/5.0 (Linux; Android 7.1.1; Pixel XL Build/NMF26O) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.91 Mobile Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2914.3 Safari/537.36 OPR/43.0.2431.0 (Edition developer)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2959.0 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2914.3 Safari/537.36 OPR/43.0.2431.0 (Edition developer)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2957.0 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/534.27 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36",
"Mozilla/5.0 (Windows; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0",
"Mozilla/5.0 (iPhone; CPU iPhone OS 10_0_2 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/10.0 Mobile/14A456 Safari/602.1",
"Mozilla/5.0 (iPhone; CPU iPhone OS 10_2 like Mac OS X) AppleWebKit/602.3.12 (KHTML, like Gecko) Version/10.0 Mobile/14C92 Safari/602.1",
"Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53 (compatible; bingbot/2.0; http://www.bing.com/bingbot.htm)",
"Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53 BingPreview/1.0b"
#	"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)",
#	"Opera/9.01 (Windows NT 5.1; U; en)",
#	"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.38 Safari/533.4",
#	"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
#	"Googlebot/2.1 ( http://www.googlebot.com/bot.html) ",
#	"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322)",
#	"Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6",
#	"Opera/9.20 (Windows NT 6.0; U; en)"
	]
	useragent = useragents[random.randint(0, len(useragents) - 1)]
	
	#### WRITE 1
	
	# Random Millisecond
	randMs = random.randint(1, 100) + 100
	
	line = clientipAddress + " - - [" + datetime.datetime.utcnow().strftime('%d/%b/%Y %H:02:35:') + str(randMs) + "] \"" + method + " " + uri + " HTTP 1.1\" " + status + " " + bytesXferred + " \"" + referralUri + "\" \"" + useragent + "\" " + timeTaken + "\n"

	if(debug):
		print(line)
	else:
		theFile.write(line)
		
	#### WRITE 2
	
	# Random Millisecond
	randMs = random.randint(1, 100) + 100
		
	line = clientipAddress + " - - [" + datetime.datetime.utcnow().strftime('%d/%b/%Y %H:39:03:') + str(randMs) + "] \"" + method + " " + uri + " HTTP 1.1\" " + status + " " + bytesXferred + " \"" + referralUri + "\" \"" + useragent + "\" " + timeTaken + "\n"
	
	if(debug):
		print(line)
	else:
		theFile.write(line)	
	
	time.sleep(random.randint(0, 2))
	
	# This ensures proper line breaking for solid tailing 
	theFile.close()
