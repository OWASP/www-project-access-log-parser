---

layout: col-sidebar
title: OWASP Access Log Parser
tags: log-parse
level: 1
type: tool
pitch: Parse and format web access logs for analysis.

---

# OALP
### OWASP Access Log Parser - Convert Web Server Access Logs to CSV

OALP was written to take web server access logs and convert them into CSV. The OALP Python script can convert logs from popular web servers such as Apache, NGINX, IIS, or similar. A specific effort was made to convert logs in the common log format and the combined log format that may be malformed. The malformation can happen due to a number of reasons, including SQL injection (SQLi), cross-site scripting (XSS), or other web server attacks.

The OALP script integrates Web_Log_Deobfuscate that deobfuscates encoding, such as that used in web server attacks, to humanly readable text. The OALP script can check log entries against the PHPIDS regex rules to identify known malicious requests. Log entries identified with formatting issues can also be logged for review as those entries may contain suspicious activity that you can review from a security perspective. 

The OALP script is recommended to ensure all web server logs can be successfully imported into analysis tools. Often analysis tools will allow for the import of malformed logs, but data may not line up correctly within fields or data is dropped. Leverage OALP to help ensure log evidence isn't missed by converting into the CSV format while attempting to format the rows correctly, so column alignment is as accurate as possible.
