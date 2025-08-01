#oalp (OWASP Access Log Parser) - Written by Ryan Boyle randomrhythm@rhythmengineering.com

#This script represents an effort to parse and properly align web logs for import into analysis tools. 
#Caution! While this script tries to not truncate data to make it align; some data truncation may occur due to malformed data (rare but will happen when a return character is included in the last field).
#Preprocessing may not be required but is recommended to avoid parsing errors
#Combined Log Format will break down to the following columns
#RemoteIP,RemoteLogName,RemoteUser,EventTime,TimeZone,Request,StatusCode,Size,Referrer,UserAgent

import csv, io, os, re, time, sys, json, threading, concurrent.futures
import logging
import jsonLogParser
from optparse import OptionParser
from Web_Log_Deobfuscate import Deobfuscate_Web_Log
from detect_log_format import get_log_format, parse_supplied_header, query_yes_no


#config section
strInputFilePath = "" #Leave blank to process the directory specified in strInputPath. Use to specify a specific log file to process
strInputPath = "" #Path to folder containing log files to format. Separate from Output path
strOutputPath = "" #Folder path to output formated logs. Make sure the folder path exists - script will not create the folder
#Input settings
inputEncoding = "utf-8" #set to "" to use system default
strLineBeginingRE = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" #regex to ensure each line starts with valid value. Set to "" to disable. default regex is for common log format and should be disabled or modfied for other formats
quotecharacter = '\"'
csv_quotechar = '\"'
strdateFormat = "%d/%b/%Y:%H:%M:%S";#apache datetime format "%d/%b/%Y:%H:%M:%S"    #IIS format "%Y-%b-%d %H:%M:%S"
outputDateFormat = '%Y-%m-%d %H:%M:%S'
header_row = "" #Leave blank to automatically detect/create a header row. # supports unquoted comma, tab, and space as argument (will be converted to quoted CSV)
columnCount = 0 #set to zero to have it dynamically identify the number of columns based on header row (first row). Note not all web servers log header rows
boolPreprocess = False #preprocessing may be required. See if you get "Error on Row: " message and if so set to True.
boolExpectDefaultFormat = True #added to improve accuracy of Common/Combined Log Format. Set to False for IIS logs
#Output settings
outputEncoding = "utf-8"
boolSingleFile = True #Create one output file or many
boolOutputInteresting = False #This can be useful for finding potential suspicious anomalies
boolDeobfuscate = False #Use Web_Log_Deobfuscate to decode fields and improve readability
boolOutputSuspicious = False #If deobfuscating entries then output suspicious entries
boolphpids = False #Run log entries against phpids rules
boolOutputIDS = False #Output PHPIDS rule match information
boolOutputUnformatted = False #This is only useful when debugging
bool_autodetect_format = True #override boolIIS with autodetection of log format
bool_log_header_row = True #Log the header_row
boolIIS = False #Use IIS settings (set boolExpectDefaultFormat = False and strdateFormat = "")
#end config section
boolSuspiciousLineFound = False #variable used to track when a line contains encoded data
phpidSignatures = {} #phpids signatures
customSignatures = {} #IDS signatures for deobfuscated log entries
boolHead = False
OutputFormat="csv" #Someday JSON will be supported
custom_ids_sig_file="custom_filter.json"
boolJSON=False
customJsonFieldNames=None
FileTypes=None
fallback_encoding = "windows-1251"
force_header_validation = True #Checks for differences in header values between input files and creates a new output file
sani_pattern = r"" #Regex used to remove sensitive data from logs
sani_replacement = "" #Replacement for sensitive data found with above regex
disabled_rules = [] #This is used to disable rules that are not useful or cause false positives.


logger = logging.getLogger(__name__)
logger.propagate = False
# create file handler which logs even debug messages
fh = logging.FileHandler('oalp.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

class bcolors: #https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="Format malformed access logs to CSV")
    parser.add_option("-i", "--input", action="store", default=None, dest="InputPath",
                      help="Path to folder containing logs to be formatted")
    parser.add_option("-o", "--output", action="store", default=None, dest="OutputPath",
                      help="Formatted log output folder path")
    parser.add_option("-d", "--deobfuscate", action="store_true", default=False, dest="boolDeobfuscate",
                      help="True or False value to deobfuscate log entries for output")
    parser.add_option("-l", "--loginteresting", action="store_true", default=False, dest="boolOutputSuspicious",
                      help="True or False value if interesting deobfuscated entries should be logged")
    parser.add_option("-p", "--phpids", action="store_true", default=False, dest="boolphpids",
                      help="True or False value if PHPIDS rule matching should be performed")
    parser.add_option("-r", "--logrules", action="store_true", default=False, dest="boolOutputIDS",
                      help="True or False value if PHPIDS rule matches should be logged")
    parser.add_option("-f", "--formatlogging", action="store_true", default=False, dest="boolOutputInteresting",
                      help="True or False value if suspicious formatting should be logged")
    parser.add_option("-m", "--MicrosoftIIS", action="store_true", default=False, dest="boolIIS",
                      help="True or False value if Microsoft IIS logs")
    parser.add_option("-t", "--file-type", action="store", default=None, dest="FileType",
                  help="Specify the type of files to process (e.g., log, csv)")
    parser.add_option("-w", "--headerrow", action="store", default=None, dest="header_row",
                      help="Override auto-detect header row with the this provided value")
    parser.add_option("-c", "--custom-filter", action="store", default="custom_filter.json", dest="custom_ids_sig_file",
                      help="Specify the custom IDS rules file to use")
    parser.add_option( "--multi-file-output", action="store_true", default=False, dest="boolMultiFile",
                  help="Specify whether each input file should have a separate output file. "
                             "If not set, all input files will be processed together, and a single output file will be generated. Default is False.")
    parser.add_option("-j","--json-logs", action="store_true", default=False, dest="boolJSON",
                  help="True or False value if log format is JSON")
    parser.add_option("--field-names", action="store", default=None, dest="customJsonFieldNames", 
                  help='JSON representation of field names mapping') 
    parser.add_option("--disabled-rules", action="store", default=None, dest="disabled_rules",
                      help="Comma-separated list of numeric rule IDs to disable (e.g., 1,2,3)")
    return parser

def config_iis():
    global boolExpectDefaultFormat, strdateFormat, strLineBeginingRE, csv_quotechar
    boolExpectDefaultFormat = False
    strdateFormat = ""
    strLineBeginingRE = ""
    csv_quotechar = '\x07' #https://stackoverflow.com/questions/494054/how-can-i-disable-quoting-in-the-python-2-4-csv-reader


def autodetect_format(file_path, header_row):
    global boolIIS
    dict_format = get_log_format(file_path,inputEncoding, quotecharacter)
    if bool_autodetect_format:
        boolIIS = dict_format['iis']
        if boolIIS:
            config_iis()
    if header_row != "":
      int_lc = len(dict_format['header_row'])
      autod_row = dict_format['header_row']
      header_list = parse_supplied_header(header_row) 
      supplied_row = header_list['header_row']
      int_hl = len(header_list['header_row'])

      if int_hl != int_lc:
          bool_continue = query_yes_no(f'The supplied header row had {int_hl} columns, but auto-detect identified the log file appears to have {int_lc}. Do you want to continue?\nHere is the auto-detect row followed by what was supplied:\n{autod_row}\n{supplied_row}\n')  # The code forces compliance on the header row. Getting the header row wrong will result in potentially undiserable results.
          if bool_continue == False:
            sys.exit()  
    if bool_log_header_row and not "json" in dict_format:
        return  '"' + '","'.join(dict_format['header_row']) + '"' #return auto detect header row
    return header_row #return user provided header_row

def phpIDS (strMatchCheck, idsFileHandle):
    global phpidSignatures
    if phpidSignatures == {}:
        with open('default_filter.json') as json_file:
            phpidSignatures = json.load(json_file)
        i=0
        #loop through and remove disabled rules
        while i < len(phpidSignatures['filters']['filter']):
          if phpidSignatures['filters']['filter'][i]['id'] in disabled_rules:
            print(f"removing rule ID {phpidSignatures['filters']['filter'][i]['id']}")
            del phpidSignatures['filters']['filter'][i]
          else:
            i += 1

    for filter in phpidSignatures['filters']['filter']:
        if re.search( filter['rule'], strMatchCheck.lower()):
            #print('id: ' + filter['id'])
            #print('rule: ' + filter['rule'])
            #print('description: ' + filter['description'])
            #print('')
            if boolOutputIDS == True:
                outputIDS = filter['id'] + "|" + filter['description'] + "|" + strMatchCheck
                logIDS(idsFileHandle, outputIDS)
            return True

def customIDS (strMatchCheck, idsFileHandle):
    global customSignatures
    if customSignatures == {}:
        try:  
          with open(custom_ids_sig_file) as json_file:
              customSignatures = json.load(json_file)
        except IOError as e:
             print(f"Error opening custom IDS signatures from file {custom_ids_sig_file}: {e.strerror}")
             sys.exit(-1)
        except json.JSONDecodeError as e:
             print(f"Error parsing custom IDS signatures from file {custom_ids_sig_file}: {e}")
             sys.exit(-1)
    for filter in customSignatures['filters']['filter']:
        if re.search( filter['rule'], strMatchCheck.lower()):
            if boolOutputIDS == True:
                outputIDS = filter['id'] + "|" + filter['description'] + "|" + strMatchCheck
                logIDS(idsFileHandle, outputIDS)
            return True
    #print(strMatchCheck)

def logIDS(fP, logline):
    fP.write("\"" + logline.replace("|", "\",\"") + "\"" + "\n")

def appendQuote(strRow):
    if right(strRow, 1) != '"':
        return strRow + '\"'
    return (strRow)

def right(s, amount):
    return s[-amount:]

def checkForFileTypeMatch(file,FileTypes):
     return any(file.endswith(suffix) for suffix in FileTypes)

def deobfuscateEncoding(line):
    global boolSuspiciousLineFound
    if (line[:1] == "+" and line.replace("+", "").replace("]", "").isnumeric()) == True:
        return line#time zone does not need deobfuscating
    strOutput = Deobfuscate_Web_Log.replaceChar(Deobfuscate_Web_Log.urldecode(line))
    strOutput = Deobfuscate_Web_Log.urldecode(strOutput)#second pass for things like %2520
    strOutput = Deobfuscate_Web_Log.replaceUnicodeChar(strOutput)
    strOutput = Deobfuscate_Web_Log.HexDecode(strOutput, '0x')
    strOutput = Deobfuscate_Web_Log.HexDecode(strOutput, '0X')
    strTmpCompare = line # used to identify supicious activity
    if boolOutputSuspicious == True and strTmpCompare != strOutput:
        if strTmpCompare.replace("%2520", " ").replace("%20", " ") != strOutput:
          boolSuspiciousLineFound = True
    return strOutput
            
def CheckRemainingColumns(row_Check, intCurrentLoc, boolNumeric):#check for special chars followed by numeric
    boolSpecialFound = False
    for intLoopRemaining in range(intCurrentLoc, len(row_Check)):
        if boolSpecialFound == True and boolNumeric == True:
            if str.isnumeric(row_Check[intLoopRemaining]):
                return intLoopRemaining
        elif boolSpecialFound == True:
            return intLoopRemaining
        elif quotecharacter in row_Check[intLoopRemaining]:
            boolSpecialFound = True
        else:
            boolSpecialFound = False
    return -1

def process_file(file_path, file_name, output_path, str_header_row = ""):
    fileProcess(file_path, file_name, output_path, str_header_row)

def process_directory(input_path, output_path, str_header_row = "", file_types=None):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        
        for file_name in os.listdir(input_path):
            if file_types and not checkForFileTypeMatch(file_name, file_types):
                continue
            
        for file_name in os.listdir(input_path):

            file_path = os.path.join(input_path, file_name)

            if os.path.isdir(file_path):
                # Recursively process subdirectories
                futures.append(executor.submit(process_directory, file_path, output_path))
            else:
                header_row = autodetect_format(file_path, str_header_row)  #todo: option to assume head row consistency and skip future checks  
                # Process individual files
                futures.append(executor.submit(process_file, file_path, file_name,output_path, header_row))

        # Wait for all futures to complete using `as_completed` iterator
        for future in concurrent.futures.as_completed(futures):
            # Handle any exceptions raised by the submitted tasks
            try:
                future.result()
            except Exception as e:
                print(f"Error processing file: {e}")
                #log error

def fileProcess(strInputFpath, strFileName, strOutPath, original_output_path="", str_header_row = "", int_resume_line=0, overide_encoding=""):
    global boolSuspiciousLineFound
    global boolHead
    global columnCount
    boolIDSdetection = False
    int_line_count = 0
    
    tmp_input_encoding = inputEncoding
    if overide_encoding != "":
        tmp_input_encoding = overide_encoding

    if boolJSON:     #checking if input file type is json and converting it CLF
       strInputFpath, tmp_header_row=jsonLogParser.parseJSONLogs(strInputFpath,strOutputPath,customJsonFieldNames)
       if bool_log_header_row:
           str_header_row = '"' + '","'.join(tmp_header_row) + '"' # for the future. Right now we only support certain fields via JSON
           str_header_row = '"ip","user","date","request","status","size"'

    if boolPreprocess == True:
        
        if not os.path.isfile(strInputFpath):
            return None
        elif not os.path.exists(strInputFpath):
            print('Error: The specified input file does not exist.')
            print('Please provide a valid input file path.')  
            return None
        tmpFilePath = strOutPath +"_preprocessed.tmp"
        if os.path.isfile(tmpFilePath):
            os.remove(tmpFilePath )
        
        with open(strInputFpath, "rt", encoding=tmp_input_encoding) as inputFile:
            for tmpLineIn in inputFile:
                tmpLineOut = tmpLineIn
                if right(tmpLineOut, 4) == '\\""\n':
                    tmpLineOut = tmpLineOut[:-4] + '\"\n'
                if "  " in tmpLineIn: #encounted with nginx logs
                    tmpLineOut = tmpLineIn.replace("  "," ")
                with io.open(tmpFilePath, "a", encoding=outputEncoding) as outputFile:
                    outputFile.write(tmpLineOut)
        strInputFpath = tmpFilePath
        print("file created for parsing " + tmpFilePath)

    if os.path.isdir(strInputFpath):
        return None
    elif not os.path.exists(strInputFpath):
        print('Error: The specified input file does not exist.')
        print('Please provide a valid input file path.')
        return None 


    file_extension = ""
    if OutputFormat:
        file_extension = "." + OutputFormat
        ## TODO support JSON output

    
    if os.path.isdir(strInputFpath):
        return None
    elif not os.path.exists(strInputFpath):
        return None
    if original_output_path == "":
        original_output_path = strOutPath
    if boolSingleFile == True:
        str_output_path = strOutPath + "_processed"
        original_out = original_output_path + "_processed"
    else:
        str_output_path = strOutPath + strFileName + "_processed"
        original_out = original_output_path + strFileName + "_processed"
    file_handle_ids = None
    if boolphpids == True and boolOutputIDS == True:
        try:
            file_handle_ids = io.open(original_out + ".IDS" + file_extension, "a", encoding=outputEncoding) #open file handle for logging IDS matches
            file_handle_ids.write('"ID,"Description","match"' + "\n")
        except IOError as e:
             print(f"Error opening file for IDS logging: {e.strerror}")
             sys.exit(-1)
    if boolphpids == True or boolOutputSuspicious == True or boolOutputInteresting == True:#open file handle for interesting log output
        try:
            fi = open(str_output_path + ".interesting" + file_extension,"a", encoding=outputEncoding) #suspicious log entry output
        except IOError as e:
            print(f"Error opening file for IDS logging: {e.strerror}")
    csv.field_size_limit(2147483647) #increase threshold to avoid length limitation errors

    with open(strInputFpath, "rt", encoding=tmp_input_encoding) as csvfile:
      bool_encoding_fallback = False # used with the next statement to close the file
      for _ in (True,): #https://stackoverflow.com/questions/11195140/break-or-exit-out-of-with-statement - user2137858  
        with io.open(str_output_path  + file_extension, "a", encoding=outputEncoding) as f:
            #print(str_header_row)
            if str_header_row != "":
                #print("header row")
                f.write(str_header_row + "\n")
                if boolphpids == True or boolOutputSuspicious == True or boolOutputInteresting == True:#log header for interesting log output
                    fi.write(str_header_row + "\n")
                boolHead = True # only write header row once
            queuedRows = []
            reader = csv.reader(csvfile, delimiter=' ', quotechar=csv_quotechar)
            try:
              for r_row in reader: #loop through each row of input
                  if int_line_count < int_resume_line:
                    next(reader)
                  queuedRows = [r_row]
                  intCheckFirstUserInput = 0
                  if strLineBeginingRE != "": #can we validate the row start with regex
                      intListCount = 0
                      boolMatch = re.match(strLineBeginingRE, r_row[0])
                      if not boolMatch: #ensure first item has a valid value
                          for testColumns in r_row:
                              intListCount +=1
                              if re.match(strLineBeginingRE, testColumns):
                                
                                  rowSlice = slice(intListCount -1, len(r_row))
                                  queuedRows = [r_row[rowSlice]]
                                  break
                  if '\n' in "".join(r_row) and columnCount > 0: #handle newline in row 
                      if len(r_row) / columnCount >= 2:
                          intListCount = 0
                          for testColumns in r_row:
                              intListCount +=1
                              if '\n' in testColumns:
                                  queuedRows = [r_row[:intListCount]]
                                  print ("Error on Row: " + "".join(r_row))
                                  queuedRows[len(queuedRows)-1][intListCount-1] = testColumns[0:testColumns.find("\n")]
                                  break
                                 

                  for row in queuedRows:
                      if columnCount == 0 and boolIIS == False:
                          columnCount = len(row)#dynamic row length

                      if "\\" in "".join(row) and boolOutputInteresting == True:
                          boolSuspiciousLineFound = True #Trigger logging suspicious line
                      outputRow = ""
                      boolSkipColumn = False
                      lastColumnEscaped = False
                      intColumnCount = 0
                      intWriteCount = 0
                      skippedColumns = 0
                      boolDateCoverted = False
                      boolExcludeRow = False #IIS headers are dropped
                      boolRequestEnding = False # this was added to track the request column. Set to true once "HTTP/" is encountered. Example: HTTP/1.1"
                    
                      for column in row:
                          intColumnCount += 1
                          boolQuoteRemoved = False
                          boolEscapeChar = False

                          #remove confidential/sensitive data match
                          saniColumn = re.sub(sani_pattern, sani_replacement, column)
                          
                          if boolphpids == True and boolSuspiciousLineFound != True:
                              boolIDSdetection = phpIDS(saniColumn, file_handle_ids)
                              boolSuspiciousLineFound  = boolIDSdetection
                          
 
                          if boolIIS == True and intColumnCount == 1 and "#Fields:" in saniColumn:
                              if boolHead == False:
                                  saniColumn = ""
                                  boolSkipColumn = True
                                  if columnCount ==0: #if dynamic header identification
                                      columnCount = len(row) -2 #dynamic row length
                              else:
                                  boolExcludeRow = True
                                  break #skip header row
                          if boolIIS == True and intColumnCount == 1 and ("#Software:" in saniColumn or "#Version:" in saniColumn or "#Date:" in saniColumn):
                              boolExcludeRow = True
                              break #drop IIS header rows

                            
                          if boolDeobfuscate == True: #perform decoding
                              saniColumn = deobfuscateEncoding(saniColumn)
                              saniColumn = str.replace(saniColumn, quotecharacter,"").replace("\n", "").replace("\rz", "") #remove format characters
                          if boolphpids == True and boolIDSdetection != True:
                              boolIDSdetection = customIDS(saniColumn.lower(),file_handle_ids)
                              boolSuspiciousLineFound = boolIDSdetection
                          if  'HTTP/' in saniColumn:
                              boolRequestEnding = True
                        
                          if '\"' in saniColumn:
                              saniColumn = str.replace(saniColumn, quotecharacter,"")  # remove quote chars
                              boolQuoteRemoved = True
                          if boolExpectDefaultFormat == True and intColumnCount == 6 and row[6].isnumeric() == True and  row[7].isnumeric() == True: #if this is the request column and next two columns are numeric then 
                              boolRequestEnding = True        #Things line up formatting wise that we don't need to check for escape characters
                          elif boolExpectDefaultFormat == True and intColumnCount == 3 and "[" == row[4][:1]: #if the column after next is the datetime field then we need to merge the next field with this one
                              boolQuoteRemoved = True
                              boolEscapeChar = True
                          elif '\\' in saniColumn:
                              if (boolDateCoverted == True): # if we have made it past the user name and date field (only need escape character checks for fields with user provided input). Example: domainname\x5Cryan.boyle  
                                  if right(saniColumn,1) == "\\" and boolDeobfuscate == False:
                                      boolQuoteRemoved = True
                                  saniColumn = str.replace(saniColumn, "\\","")  #remove escape character
                                  boolEscapeChar = True
                          elif boolExpectDefaultFormat == True and intColumnCount == 6 and ('GET' in saniColumn or 'POST' in saniColumn or 'PUT' in saniColumn  or 'HEAD' in saniColumn  or 'PUT' in saniColumn  or 'DELETE' in saniColumn) and boolRequestEnding == False:
                              boolEscapeChar = True #specific way to identify the request column and combine
                          elif boolExpectDefaultFormat == True and intColumnCount > 6 and boolRequestEnding == False:
                              boolEscapeChar = True #specific way to identify the request column and combine
                          elif boolExpectDefaultFormat == True and intColumnCount == columnCount and len(row) - intColumnCount - skippedColumns != columnCount - intColumnCount:
                              boolEscapeChar = True #This will cause the script to add up all final columns into the last one
                          if boolDateCoverted == False and saniColumn[0:1] == "[":# format date time
                              boolDateCoverted = True
                              logDateTime = time.strptime( saniColumn[1:], strdateFormat)
                              saniColumn = time.strftime(outputDateFormat, logDateTime)


                          if boolEscapeChar == True and len(row) > columnCount and boolSkipColumn == False and boolQuoteRemoved == True:  #escaped character and column mismatch
                        
                              if len(row) - intColumnCount != 0:
                                  outputRow = outputRow + ',"' + saniColumn #add new column
                              else:
                                  outputRow = outputRow + " " + saniColumn #continue column and add separator char back
                              intWriteCount += 1
                              if len(row) - intColumnCount - skippedColumns != columnCount - intColumnCount: #more columns than what is expected so combine next column
                                  boolSkipColumn = True
                          elif boolSkipColumn == True and (len(row) - intColumnCount - skippedColumns != columnCount - intColumnCount): #still more columns than what is expected so combine next column
                              skippedColumns +=1
                              if boolHead == False and boolIIS == True and intColumnCount == 1: #IIS header row manipulation
                                  outputRow = "\"" #excluding #Fields: and replacing with a qoute to start our next field
                                  continue
                              if intCheckFirstUserInput == 0:
                                  intCheckFirstUserInput = CheckRemainingColumns(row, intColumnCount, True) # row, currentColumn, boolCheckNumeric
                              if  intCheckFirstUserInput >= intColumnCount:#check for special chars followed by number (In apache logs this is the first non system/user provided column that is followed by a status code)
                                  outputRow = outputRow + " " + saniColumn #continue column and add separator char back
                              elif boolQuoteRemoved == True and CheckRemainingColumns(row, intColumnCount, False) <= intColumnCount and not (intColumnCount - skippedColumns == columnCount and len(row) - intColumnCount != 0):#check for special chars ensuring we don't close the column if there is still items to add 
                                  outputRow = outputRow + " " + saniColumn + '"' #Finish and close column
                                  boolSkipColumn = False
                                  intWriteCount += 1
                              elif boolHead == False and boolIIS == True and intColumnCount == 2: #IIS header row manipulation continuation
                                  outputRow = outputRow + saniColumn #this is actually our first output value entry as we skipped #Fields:
                                  boolHead = True
                              else:
                                  outputRow = outputRow + " " + saniColumn #continue column and add separator char back
                          elif boolSkipColumn == True and len(row) - intColumnCount - skippedColumns == columnCount - intColumnCount: #New columns are just right
                              skippedColumns +=1
                              outputRow = appendQuote(outputRow) + ',"' + saniColumn + '"' #Close column and add new column
                              boolSkipColumn = False
                              intWriteCount += 1



                          elif outputRow == "": # first column in new row
                              outputRow = '"' + saniColumn + '"'
                              intWriteCount += 1
                    
                          else: # add new column
                              if boolEscapeChar == True:
                                  lastColumnEscaped = True
                                  outputRow = appendQuote(outputRow) + ',"' + saniColumn #start new column
                                  boolSkipColumn = True 
                              elif intColumnCount - skippedColumns >= columnCount and len(row) == intColumnCount and columnCount != len(row): #we've got too many columns. Mash last one together
                                  outputRow = appendQuote(outputRow) + ',"' + saniColumn + '"' #Close column and add final column
                              elif intWriteCount + 1 == columnCount and len(row) > intColumnCount:
                                  outputRow = appendQuote(outputRow) + ',"' + saniColumn #start new column
                              else:
                                  outputRow = outputRow + ',"' + saniColumn + '"'#start and close new column
                                  intWriteCount += 1

                      if len(row) < columnCount:
                          for x in range(0,columnCount - len(row)):
                              outputRow = appendQuote(outputRow) + ',\"ParseError\"'
                      if right(outputRow, 1) != '\"':
                          #outputRow = outputRow + '\"'
                          if boolOutputUnformatted == True:
                              with io.open(str_output_path + ".Unformatted", "a", encoding=outputEncoding) as fU:#Unformatted output that eluded a final quote
                                  fU.write(outputRow + "\n")
                      outputRow = appendQuote(outputRow) 

                      if boolExcludeRow == False:
                          f.write(outputRow + "\n")
                          if boolSuspiciousLineFound == True:
                              boolSuspiciousLineFound = False
                              boolIDSdetection = False
                              fi.write(outputRow + "\n")
                  int_line_count +=1
            except UnicodeDecodeError:
              logger.error("Error: File not encoded in UTF-8: %s", strInputFpath, exc_info=True)
              if fallback_encoding != "" and fallback_encoding != overide_encoding: #is fallback encoding configured and have we already tried it
                logger.info("Info: Attempting backup encoding: %s", fallback_encoding)
                #need to exit out of the with statement to unlock the file
                bool_encoding_fallback = True
                print(f"{bcolors.FAIL}Error: File not encoded in UTF-8 (see oalp.log for exception details). Trying a different encoding for file {strInputFpath}{bcolors.ENDC}")
                break
              print(f"{bcolors.FAIL}Error: File not encoded in UTF-8 (see oalp.log for exception details). Try a different encoding for file {strInputFpath}{bcolors.ENDC}")
              print(f"{bcolors.WARNING}Warning: File encoding changes may be an indicator of log tampering {bcolors.ENDC}")
      if bool_encoding_fallback == True:
        print(f"{bcolors.WARNING}Warning: File encoding changes may be an indicator of log tampering {bcolors.ENDC}")      
        return fileProcess(strInputFpath, strFileName, strOutPath, str_header_row = "", int_resume_line=int_line_count, overide_encoding=fallback_encoding)
              

    if os.path.isfile(strInputFilePath +".tmp"):
        os.remove(strInputFilePath +".tmp")     
    if boolphpids == True and boolOutputIDS == True:
        file_handle_ids.close() #close file handle for IDS log output
    if boolphpids == True or boolOutputSuspicious == True or boolOutputInteresting == True:#open file handle for interesting log output
        fi.close() #close file handle for interesting log output

parser = build_cli_parser()
opts, args = parser.parse_args(sys.argv[1:])
if opts.InputPath:
    strInputPath = opts.InputPath
    print (f"input={strInputPath}")
if opts.OutputPath:
    strOutputPath = opts.OutputPath
    print (f"output={strOutputPath}")
if (not strInputPath and not strInputFilePath) or not strOutputPath:
    if(not strInputPath and not strInputFilePath and not strOutputPath):
        print ("Missing required parameters -i and -o")
    elif(not strInputPath and not strInputFilePath):    
        print ("Missing required parameter -i")
    elif(not strOutputPath):    
        print ("Missing required parameter -o")
    print('Example usage: python olap.py -i /path/to/input.log -o /path/to/output.log')
    sys.exit(-1)
if opts.boolDeobfuscate:
    boolDeobfuscate = opts.boolDeobfuscate
if opts.boolOutputSuspicious:
    boolOutputSuspicious = opts.boolOutputSuspicious
if opts.boolphpids:
    boolphpids = opts.boolphpids
if opts.boolOutputInteresting:
    boolOutputInteresting = opts.boolOutputInteresting
if opts.boolOutputIDS:
    boolOutputIDS = opts.boolOutputIDS
if opts.FileType:
    FileTypes=opts.FileType.split(',')
if opts.boolMultiFile:
    boolSingleFile=not opts.boolMultiFile
if opts.boolIIS:
    boolIIS = opts.boolIIS
if opts.boolJSON:
    boolJSON=opts.boolJSON
    strLineBeginingRE = ""
    boolExpectDefaultFormat = False
if boolIIS == True:
    config_iis()
if opts.header_row:
    header_row = opts.header_row
if opts.custom_ids_sig_file:
    custom_ids_sig_file = opts.custom_ids_sig_file
if opts.disabled_rules:
    disabled_rules = [x.strip() for x in opts.disabled_rules.split(',') if x.strip().isdigit()]
    print(disabled_rules)


if strInputFilePath == "":
    if os.path.isfile(strInputPath):#check if a file path was provided instead of a folder
            strInputFilePath = strInputPath #use file instead of folder
            strInputPath = ""

def find_unique_filename(base_filename, str_file_extension):
    """
    Generates a unique filename by appending a number if the base filename exists.
    """
    counter = 0
    while True:
        if counter == 0:
            filename = f"{base_filename}"
        else:
            filename = f"{base_filename}_{counter}"
        
        if not os.path.exists(f"{filename}_processed.{str_file_extension}"):
            print(f"New file name: {filename}")
            return filename
        counter += 1

def header_check(str_previous_header, str_new_header, str_output_path):
    if not str_previous_header: #First file we will not have a previous value
        return str_output_path, str_new_header #return current output path and header to be written
    if str_previous_header and str_previous_header != str_new_header: #this needs moved into a function and happen every time a header may change
        print(f"Header changed for file {file} from \n {previous_header} \nto \n {header_row}\nDue to log format change the script will create a new output file")
        return find_unique_filename(strOutputPath, OutputFormat), str_new_header
    return str_output_path, "" #return current output path and no header since it was already written
    
previous_header = None
original_out_path = strOutputPath
if os.path.isdir(strInputPath):
    bool_header_logged = False
    if not boolSingleFile:
     
     process_directory(strInputPath, strOutputPath, header_row, file_types=FileTypes)
    else:
      for file in os.listdir(strInputPath):
          if os.path.isdir(os.path.join(strInputPath, file)):
              for subfile in os.listdir(os.path.join(strInputPath, file)):
                  print(os.path.join(os.path.join(strInputPath, file), subfile))
                  if not bool_header_logged or force_header_validation:
                      
                      header_row = autodetect_format(strInputFilePath, header_row)

                  strOutputPath, tmp_header = header_check(previous_header, header_row, strOutputPath) # a different/new header means we need a new file for CSV output (once we support JSON output this will not matter for that)
                  fileProcess(os.path.join(os.path.join(strInputPath, file), subfile), subfile, strOutputPath,str_header_row=tmp_header, original_output_path=original_out_path)
                  bool_header_logged = True
                  previous_header = header_row
          else:
              if not bool_header_logged or force_header_validation:
                header_row = autodetect_format(os.path.join(strInputPath, file), header_row)
              strOutputPath, tmp_header = header_check(previous_header, header_row, strOutputPath) # a different/new header means we need a new file for CSV output
              fileProcess(os.path.join(strInputPath, file), file, strOutputPath, str_header_row=tmp_header, original_output_path=original_out_path)
              previous_header = header_row
          bool_header_logged = True
          header_row = ""
elif os.path.isfile(strInputFilePath):
    fileName = os.path.basename(strInputFilePath)
    header_row = autodetect_format(strInputFilePath, header_row)
    
    fileProcess(strInputFilePath, fileName, strOutputPath, str_header_row=header_row)
else:
    print(f"{bcolors.FAIL}Error: Path could not be processed. Check that it exists and you have access to it: {strInputPath}{bcolors.ENDC}")


print("Completed!")
