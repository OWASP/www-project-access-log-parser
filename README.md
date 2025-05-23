# OALP
### OWASP Access Log Parser - Convert Web Server Access Logs to CSV

OALP was written to take web server access logs and convert them into CSV. The OALP Python script can convert logs from popular web servers such as Apache, NGINX, IIS, or similar. A specific effort was made to convert logs in the common log format and the combined log format that may be malformed. The malformation can happen due to a number of reasons, including SQL injection (SQLi), cross-site scripting (XSS), or other web server attacks.

The OALP script integrates Web_Log_Deobfuscate that deobfuscates encoding, such as that used in web server attacks, to humanly readable text. The OALP script can check log entries against the PHPIDS regex rules to identify known malicious requests. Log entries identified with formatting issues can also be logged for review as those entries may contain suspicious activity that you can review from a security perspective. 

The OALP script is recommended to ensure all web server logs can be successfully imported into analysis tools. Often analysis tools will allow for the import of malformed logs, but data may not line up correctly within fields or data is dropped. Leverage OALP to help ensure log evidence isn't missed by converting into the CSV format while attempting to format the rows correctly, so column alignment is as accurate as possible.

The script may need to be modified to ensure proper operation with the logs you are trying to format. This is because there are many ways in which web servers log access. For example, some logs may not provide a referrer or user agent field while others do. Edit the config section of the script per the notes for each variable.

Options:

  -h, --help            show this help message and exit

  -i INPUTPATH, --input=INPUTPATH
                        Path to folder containing logs to be formatted

  -t FILETYPE, --file-type=FILETYPE
                        Specify the type of files to process (e.g., log, csv)

  -o OUTPUTPATH, --output=OUTPUTPATH
                        Formatted log output folder path

  -d, --deobfuscate     True or False value to deobfuscate log entries for
                        output

  -l, --loginteresting  True or False value if interesting deobfuscated
                        entries should be logged

  -p, --phpids          True or False value to perform PHPIDS rule matching
                        

  -r, --logrules        True or False value if PHPIDS rule matches should be
                        logged

  -f, --formatlogging   True or False value if suspicious formatting should be
                        logged
                        
  -m, --MicrosoftIIS    True or False value if target logs are IIS
                        
  -w, --headerrow       Override auto-detect header row with the this provided value
                        
  --multi-file-output   Specify whether each input file should have a separate output file. If not set, all input files will be processed together, and a single output file will be generated. Default is False.

  -c, --custom-filter   Specify the custom IDS rules file to use

  -j, --json-logs       True or False value if log format is JSON
  --field-names=CUSTOMJSONFIELDNAMES
                        JSON representation of field names mapping

<br /> 
<br /> 
Example:

                  oalp.py -i c:\oalp\Web_Log_Deobfuscate\Example_Logs\access.log -o c:\processed_logs\outputfile


External references:

[Formatting and Deobfuscating Web Logs](https://www.randomsecurityblog.com/2020/02/formatting-and-deobfuscating-web-logs.html)

[Formatting and Deobfuscating Web Logs - Integrating Deobfuscation](https://www.randomsecurityblog.com/2020/02/formatting-and-deobfuscating-web-logs_15.html)

[Formatting and Deobfuscating Web Logs - Detecting Suspicious Activity](https://www.randomsecurityblog.com/2020/03/formatting-and-deobfuscating-web-logs.html)

## Contributions
* ### [P-venkatsai](https://github.com/P-venkatsai) - The first community contribution and a significant one at that.
