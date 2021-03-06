#=====================================================================
# REPORITNG FROM PRTG
#=====================================================================
# Author: Alvaro Paricio
#=====================================================================
import pandas as pd
import requests
import os
import re
import json
import pprint
import sys
import argparse
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

api_req_data=""
api_struct={}

opts={}

pp = pprint.PrettyPrinter(indent=3)

# ------------------------------------------------------------------
def api_query(title,item):
    # Get first response for headers: get total number of records
    # {"expand":"schema,names","startAt":0,"maxResults":50,"total":445503,"issues"
    issues=[]
    rows=1000
    startAt=0
    total=1
    url_opts=''

    print( "---------------------------\nPRTG: retrieving "+title)
    # -- Do query --
    # url_opts="startAt={}&maxResults={}&".format( startAt, rows )
    url_opts="username={}&passhash={}&count={}".format( opts['api_user'], opts['api_passhash'], opts['api_count'])
    url=opts['api_url_api']+'/table.xml?'+url_opts+"&"+item["query"]
    print( "API CALL: "+url)
    response = requests.get(url,
			verify=False)
#			auth=(opts['api_user'], opts['api_passhash']),
    print( response )
    if response.status_code != 200:
            print("   --> ERROR:", str(response))
            return issues
    print( response.text )
#        jresp = json.loads(response.text)
#        curr_rows=len(jresp['issues'])
#        total=jresp['total']
#        flag_continue=True
#        for i in jresp['issues']:
#            if flag_continue:
#                t = api_translate_ticket(i)
#                issues.append(t)
#                #flag_continue=False
#        print( "   --> GOT {} / {}  records".format(len(jresp['issues']), jresp['total']))
#        startAt += curr_rows
#    # df = pd.DataFrame(issues,index=['key'])
#    df = pd.DataFrame(issues)
#    # df = pd.DataFrame(issues)
#    api_replace_headers(df)
#    if flag_dump_raw:
#        print( "* Dumping to raw data file:" + item["raw"])
#        df.to_csv(item["raw"]+"_raw1.csv", sep=';')
#    if flag_dump_raw:
#        print( "* Dumping to raw-translated data file:" + item["raw"])
#        df.to_csv(item["raw"]+"_raw2.csv", sep=';')
#
#    df1.to_csv(item["file"]+".csv", sep=';')
    print( "* Done\n" )
    return issues

# ------------------------------------------------------------------
def generate_report(prefix, raw_prefix, from_date, to_date):
    queries_pool= {}

    queries_pool['PRTG / HOSTS']={
        "file": "{}_devices".format(prefix),
        "raw": "{}_devices".format(raw_prefix),
        "query": 'content=devices&columns=objid,group,host,device,sensor,status,parent,parentid,location,type,name,message&output=csvtable'.format(from_date, to_date)}
        #"query": 'content=sensortree&output=csvtable'.format(from_date, to_date)}
        #"query": 'content=devices&output=csvtable&columns=device,host'.format(from_date, to_date)}

#    queries_pool['PRTG / SENSORTREE']={
#        "file": "{}_sensortree".format(prefix),
#        "raw": "{}_sensortree".format(raw_prefix),
#        "query": 'content=sensortree&output=csvtable'.format(from_date, to_date)}

    for i in queries_pool:
        issues = api_query(i, queries_pool[i])

# ------------------------------------------------------------------
def printable_date(prefix,in_date):
  the_date = datetime.strptime(in_date, '%Y-%m-%d')
  return "{}{}".format( prefix, datetime.strftime( the_date, '%Y%m%d' ))

# ------------------------------------------------------------------
def printable_hour():
  return datetime.strftime( datetime.now(), '_%H' )

# ------------------------------------------------------------------
def normalize_date(in_date):
  out_date=in_date
  the_date=datetime.now()
  try:
    days = int(in_date)
    the_date = the_date + timedelta(days=days)
    out_date=datetime.strftime( the_date, '%Y-%m-%d' )
  except ValueError:
    if in_date == 'now':
      out_date=datetime.strftime( the_date, '%Y-%m-%d' )
  return out_date

# ------------------------------------------------------------------
def getConfig():
  opts={}

  parser = argparse.ArgumentParser()
  parser.add_argument("-f","--from-date", help="From date, in YYYY-MM-DD|now|-D format", default="-1")
  parser.add_argument("-t","--to-date", help="To date, in YYYY-MM-DD|now|-D format", default="now")
  parser.add_argument("-v","--verbose", help="Verbose output", default=False, action="store_true")
  parser.add_argument("-g","--group", help="Report group: daily|weekly|manual", default="daily")
  parser.add_argument("-H","--print-hour", help="Print hour", default=False, action="store_true")
  parser.add_argument("-d","--out-dir", help="Output directory", default="/reports/public/jira")
  parser.add_argument("-r","--raw-dir", help="Raw data output directory", default="/reports/raw/jira")
  opts = vars(parser.parse_args())

  opts['out_dir']= opts['out_dir'] + '/' + opts['group']
  if not os.path.exists(opts['out_dir']):
    os.makedirs(opts['out_dir'])

  opts['raw_dir']= opts['raw_dir'] + '/' + opts['group']
  if not os.path.exists(opts['raw_dir']):
    os.makedirs(opts['raw_dir'])

  opts['from_date'] = normalize_date( opts['from_date'] )
  opts['to_date']   = normalize_date( opts['to_date'] )
  opts['pp_from_date'] = printable_date( 'from', opts['from_date'] )
  opts['pp_to_date']   = printable_date( 'to', opts['to_date'] )
  opts['pp_hour'] = printable_hour() if opts['print_hour'] else ''

  opts['api_url_api']="https://prtg.xtratelecom.es/api"
  opts['api_user']="alvaro.paricio@masmovil.com"
  opts['api_passw']="g9W3bRtD3zzv"
  opts['api_passhash']="2990680966"
  opts['api_count']="10000"

  print("*** Collect from date: {}".format(opts['from_date']))
  print("*** Collect to   date: {}".format(opts['to_date']))

  return opts

# ------------------------------------------------------------------
opts = getConfig()
now=datetime.now()
prefix='{}/PRTG_{}_{}{}'.format(
				opts['out_dir'],
				opts['pp_from_date'],
				opts['pp_to_date'],
				opts['pp_hour']
				)
raw_prefix='{}/PRTG_{}_{}{}'.format(
				opts['raw_dir'],
				opts['pp_from_date'],
				opts['pp_to_date'],
				opts['pp_hour']
				)
issues = generate_report(prefix,raw_prefix,opts['from_date'], opts['to_date'])

