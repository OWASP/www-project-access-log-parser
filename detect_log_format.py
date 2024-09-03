import csv
import re
import time
strLineBeginingRE = "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" #regex to ensure each line starts with valid value. Set to "" to disable. default regex is for common log format and should be disabled or modfied for other formats
strdateFormat = "%d/%b/%Y:%H:%M:%S"
dict_header_info = {}

def get_log_format(strInputFpath, inputEncoding,quote_char):
  list_header = []
  first_row_read = False
  bool_iis_marker = False
  with open(strInputFpath, "rt", encoding=inputEncoding) as f:
    for line in f:
       if first_row_read == True:
         break
       print(line.rstrip())
       if len(line)>0 and line[0] != "#":
        first_row_read = True
        logreader = csv.reader(line.splitlines(), delimiter=' ', quotechar=quote_char)
        for row in logreader:
          print(row)
          bool_date_found = False 
          bool_request_ending = False # this was added to track the request column. Set to true once "HTTP/" is encountered. Example: HTTP/1.1"
                    
          boolMatch = re.match(strLineBeginingRE, row[0])
          if boolMatch:
            list_header = ["ip"]
            if row[1] == "-":
              list_header.append("identd")
              list_header.append("user")
            if bool_date_found == False and row[3][0:1] == "[":# format date time
              boolDateCoverted = True
              try:
                logDateTime = time.strptime( row[3][1:], strdateFormat)
              except:
                boolDateCoverted = False
                print("Warning! Date format does not match the default. Update strdateFormat variable with correct values")
              list_header.append("time")
              list_header.append("offset")
              offset = 0
              if ('GET' in row[5] or 'POST' in row[5] or 'PUT' in row[5]  or 'HEAD' in row[5]  or 'PUT' in row[5]  or 'DELETE' in row[5]) and bool_request_ending == False:
                if 'HTTP/' in row[5]:
                  list_header.append("request")
                  bool_request_ending = True
                  offset = -2 # column combines request, method, and resource
                else:
                  list_header.append("method")
                  list_header.append("resource")
                  if  'HTTP/' in row[7]:
                    boolRequestEnding = True
                    list_header.append("protocol")
                if row[8 + offset].isnumeric() == True and (row[9 + offset].isnumeric() == True or row[9 + offset] == "-"): #if this is the request column and next two columns are numeric then 
                  boolRequestEnding = True 
                  list_header.append("status")
                  list_header.append("size")
                print(len(row))
                if len(row) > 11 + offset:
                  list_header.append("referrer")
                  list_header.append("useragent")
                if len(row) > 12 + offset:
                  x = range(len(row) - (12 + offset))
                  for n in x:
                    list_header.append("field" + str(n))
              dict_header_info["header_row"] = list_header
              dict_header_info["iis"] = False


       if "#Software: Microsoft Internet Information Services" in line:
         bool_iis_marker = True
       elif "#Fields: " in line:
         tmp_header = line.replace("#Fields: ","").rstrip()
         list_header = tmp_header.split()
         print(list_header)
         dict_header_info["header_row"] = list_header
         dict_header_info["iis"] = True
         break
  #dict_return = {"bool_iis":bool_iis_marker, "dict_columns":dict_header_info}  
  return dict_header_info

def parse_supplied_header(supplied_header):

  if ", " in supplied_header:
    print("comma space")
    list_header = supplied_header.split(", ")
  elif "," in supplied_header:
    print("comma")
    list_header = supplied_header.split(",")
  elif "\t" in supplied_header:
    print("tab")
    list_header = supplied_header.split("\t")
  elif " " in supplied_header:
    print("space")
    list_header = supplied_header.split(" ")
  dict_header_info["header_row"] = list_header
  return dict_header_info
    
