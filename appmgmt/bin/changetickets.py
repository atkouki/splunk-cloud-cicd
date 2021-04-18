import datetime,os, re

jiraLines = [
"2010-09-28 00:15:30 Type=ChangeWindow WindowStart=2010-09-28 00:00:00 WindowEnd=2010-09-28 00:30:00 TargetServer=mysql-2.splunk.com TicketId=10020 User=joe@flowershop.com TargetClass=mysql TargetChangeObject=CoreConfig TargetChangeProperty=MaxMemory TargetChangePropertyValue=2048",
"2010-09-28 00:15:30 Type=ChangeWindow WindowStart=2010-09-28 01:00:00 WindowEnd=2010-09-28 01:30:00 TargetServer=mysql-1.splunk.com TicketId=10021 User=peter@flowershop.com  TargetClass=mysql TargetChangeObject=CoreConfig TargetChangeProperty=MaxLogSizeMB TargetChangePropertyValue=256"
]	
	
for lines in jiraLines:
	# Replace stuff
	time = datetime.datetime.utcnow()
	line = re.sub('\d{4}-\d{2}-\d{2}', time.strftime('%Y-%m-%d'), lines)
	print (line + "\n"),
