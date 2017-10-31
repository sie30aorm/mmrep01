#=====================================================================
# REPORTING FROM JIRA
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

jira_req_data=""
jira_struct={}

opts={}

flag_get_masivas_red=True
flag_get_masivas_sist=True

flag_extract_and_translate=False

flag_verbose=False
flag_dump_raw=True
label_tecnologia='Tecnologia (Servicio) inicial'
label_dpto_destino='Departamento destino'
label_dpto_origen='Departamento Origen'

nivel_servicio={
  'Atencion Al Cliente':'N1',
  'Atencion Al Cliente - ACTIVACIONES OPERADORES':'N2',
  'Atencion Al Cliente - ATENCION EMPRESAS':'N1',
  'Atencion Al Cliente - ATENCION OPERADORES':'N1',
  'Atencion Al Cliente - SOPORTE EMPRESAS':'N1',
  'Atencion Al Cliente - SOPORTE OPERADORES':'N1',
  'Atencion Al Cliente - MANTENIMIENTO EMPRESAS':'N2',
  'Atencion Al Cliente - MANTENIMIENTO NEUTRA':'N2',
  'Atencion Al Cliente - MANTENIMIENTO OPERADORES':'N2',
  'Atencion Al Cliente - MANTENIMIENTO RESELLER':'N2',
  'Departamento Financiero':'N3-FIN',
  'Departamento Financiero - FINANCIERO':'N3-FIN',
  'Departamento Red - ING.DATOS':'N2',
  'Departamento Red - ING.VOZ':'N2',
  'Departamento Red - O&M':'N2',
  'Departamento Red - PLATAFORMAS':'N2',
  'Departamento Sistemas':'N1',
  'Departamento Sistemas - MVNO':'N1',
  'Departamento Sistemas - SISTEMAS':'N1',
  'Implantacion - IMPLANTACION-INCIDENCIAS':'SD',
  'Portabilidad':'SD',
  'Provision':'SD',
  'Provision - PROVISION':'SD',
  'Provision - PROVISION-BAJAS':'SD',
  '':'N1'
}

tipo_inc_por_tech = {
  'ADSL':'DATOS',
  'CIRCUITOS':'DATOS',
  'DATOS':'DATOS',
  'SATELITE':'DATOS',
  'DATA SATELITE':'DATOS',
  'LTE':'DATOS',
  'AMLT':'VOZ',
  'ENDPOINT':'VOZ',
  'MERCURIO':'VOZ',
  'TRUNKSIP':'VOZ',
  'VOZ':'VOZ',
  'MOVIL':'MOVIL',
  'FAX TO EMAIL':'SVA',
  'MSO365':'SVA',
  'SVAs':'SVA',
  'SVA':'SVA',
  'CLOUD':'OTROS'
}

pp = pprint.PrettyPrinter(indent=3)

# ------------------------------------------------------------------
def jira_get_fields():
    global jira_struct
    # {'custom': True,
    url=opts['jira_url_api']+'/field'
    print( "JIRA: retrieving "+'CUSTOM FIELDS STRUCTURE')
    response = requests.get(url, auth=(opts['jira_user'], opts['jira_passw']))
    print( response )
    if response.status_code != 200:
        print("ERROR:", str(response))
        return
    jresp = json.loads(response.text)
    jira_struct['custom']={}
    jira_struct['standard']={}
    for f in jresp:
        f_id=f['id']
        f_name=f['name']
        if( f['custom'] ):
            jira_struct['custom'][f_id]=f_name
        else:
            jira_struct['standard'][f_id]=f_name
        if flag_verbose:
            print(str(f_id)+","+f_name)
    print( "Done\n" )

def jira_translate_ticket(issue):
    #print("------------------------------")
    #print( issue )
    #print("------------------------------")
    ticket={}
    ticket['id']=issue['id']
    ticket['key']=issue['key']
    ticket['jira_parent'] = ''
    ticket['jira_parent_type'] = ''
    ticket['jira_parent_relation'] = ''

    for f in issue['fields']:
        if f == 'issuelinks' and len(issue['fields'][f])>0:
          #print("*** DETECTED issuelinks len={}***".format( len(issue['fields'][f])))
          issue1 = issue['fields'][f][0]
          if 'outwardIssue' in issue1:
                #print("***         issuelinks WITH CONTENTS***")
                ticket['jira_parent'] = issue1['outwardIssue']['key']
                ticket['jira_parent_type'] = issue1['type']['name']
                ticket['jira_parent_relation'] = issue1['type']['outward']
                #print("--> Detected massive: {}".format(ticket['jira_parent']))
        else:
          v=issue['fields'][f]
          label=f
          if False:
            if 'customfield' in f:
                label=jira_struct['custom'][f]
            else:
                label=jira_struct['standard'][f]
          if v == None:
            ticket[label]=''
          else:
            if isinstance(v,(list, tuple, dict)):
                if 'value' in v:
                    ticket[label]=v['value']
                elif 'name' in v:
                    ticket[label]=v['name']
                else:
# CANAL Y SEGMENTO VIENEN ASI:
# [{'id': '12918', 'self': 'https://jira.masmovil.com/rest/api/2/customFieldOption/12918', 'value': 'Venta directa'}]
# [{'value': 'N/D', 'id': '12917', 'self': 'https://jira.masmovil.com/rest/api/2/customFieldOption/12917'}]
                    #if 'customfield' in label:
                    #  print("--> LABEL: "+jira_struct['custom'][label])
                    #print(v)
                    if isinstance(v,list) and len(v) == 1 and isinstance(v[0],dict) and 'value' in v[0]:
                      ticket[label]=v[0]['value']
                    else:
                      ticket[label]=''
                if 'child' in v:
                    child = v['child']
                    if isinstance(child,(list, tuple, dict)):
                        if 'value' in child:
                            ticket[label]='{} - {}'.format(ticket[label], child['value'])
            else:
                ticket[label]=v
    if flag_verbose:
        pp.pprint(issue)
        print("-----------------------")
        pp.pprint(ticket)
        print("")
    return ticket

# ------------------------------------------------------------------
def jira_replace_headers(df):
    cols2=[]
    #print(df.columns)
    for i in df.columns:
        if 'customfield' in i:
            label=jira_struct['custom'][i]
        else:
            #label=jira_struct['standard'][i]
            label=i
        cols2.append( label )
    df.columns = cols2

# ------------------------------------------------------------------
is_blank = re.compile('\s*')
def set_workdone( row ):
    val = "Solicitud"
    if not row['issuetype'].lower() == "solicitud":
        aux=row['summary'].lower()
        if  is_blank.match(aux):
            val = "Configuracion" if any(x in aux for x in ["config","instal"]) else "Averia"
    #print( row['Tipo de Incidencia']+": "+row['Resumen']+ " ==> "+ row['Averia/Config'])
    return val

# ------------------------------------------------------------------
param_fcr_threshold = 60*30
def set_first_call_resolution(row):
  global param_fcr_threshold
  timeval_fcr = row['timeval_fcr']
  secs = timeval_fcr.total_seconds()
  if( secs > 0 and secs < param_fcr_threshold ):
    return 'OK'
  return 'KO'

# ------------------------------------------------------------------
def set_first_call_resolution_time(row):
    timeval_created =  row['timeval_created']
    if not row['resolutiondate'] or row['resolutiondate'] == '':
      now = datetime.now()
      timeval_fcr=now-now
    else:
      timeval_resolutiondate = datetime.strptime(row['resolutiondate'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
      timeval_fcr=timeval_resolutiondate-timeval_created
    return timeval_fcr

# ------------------------------------------------------------------
def set_open_time(row):
    timeval_created =  row['timeval_created']
    if not row['resolutiondate'] or row['resolutiondate'] == '':
        timeval_diff=datetime.now()-timeval_created
    else:
        timeval_resolutiondate = datetime.strptime(row['resolutiondate'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        timeval_diff=timeval_resolutiondate-timeval_created
    return timeval_diff

# ------------------------------------------------------------------
def fix_tipo_incidencia(row):
  if row[label_tecnologia] == '':
     row[label_tecnologia] = row['Tipo Ticket Incidencia']

  if row['Tipo Ticket Incidencia'] == '':
     row['Tipo Ticket Incidencia'] = row[label_tecnologia]

# ------------------------------------------------------------------
def jira_calculate_columns(df):
    time_value=lambda x: datetime.strptime(x.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    format_time=lambda x: datetime.strftime( x, '%d/%m/%Y %H:%M:%S' )
    resolved_time=lambda x: '' if x == '' else datetime.strftime( datetime.strptime(x.split('.')[0], '%Y-%m-%dT%H:%M:%S'), '%d/%m/%Y %H:%M:%S' )
    classify_duration=lambda x: '<1D' if x.days < 1 else '<2D' if x.days < 2 else '<5D' if x.days < 5 else '<7D' if x.days < 7 else '>7D'
    get_duration=lambda x: "{}".format(x.days+x.seconds/86400).replace('.', ',')
    url_ticket=lambda x: "{}/{}".format( "https://jira.masmovil.com/browse/", x)
    get_duration=lambda x: "{}".format(x.days+x.seconds/86400).replace('.', ',')
    # SLA: ticket updated made in hours
    get_sla_is_attended=lambda x: 'OK' if x.days*24+x.seconds/3600 < 24 else 'KO'
    get_service_grouped=lambda x: '' if not x else str(x).split('-')[0].strip()
    get_service_type=lambda x: '' if not x or not '-' in str(x) else str(x).split('-')[0]
    get_service_problem=lambda x: '' if not x or not '-' in str(x) else str(x).split('-')[1]
    set_support_level=lambda x: 'Otros' if not x in nivel_servicio else nivel_servicio[x]
    adjust_tipo_inc=lambda x: tipo_inc_por_tech[str(x).upper()] if str(x).upper() in tipo_inc_por_tech else 'OTROS'
    get_canal=lambda x: 'unknown' if not x else x if x in ('web.cable','MasBss') else 'operador'
    check_excepciones=lambda x: '' if not x else 'QUANTIS' if 'quantis' in x.lower() else ''
    # df.apply( fix_tipo_incidencia, axis=1 )
    
    now = datetime.now()
    df['timeval_created']=df['created'].map( time_value )
    df['timeval_updated']=df['updated'].map( time_value )
    # df['timeval_diff']=df['timeval_updated']-df['timeval_created']
    df['timeval_diff']=df.apply( set_open_time, axis=1 )
    df['timeval_unattended']=now - df['timeval_updated']
    #First call resolution
    df['timeval_fcr']=df.apply( set_first_call_resolution_time, axis=1 )
    df['fcr']=df.apply( set_first_call_resolution, axis=1 )

    df['fmt_created']=df['timeval_created'].map( format_time )
    df['fmt_updated']=df['timeval_updated'].map( format_time )
    df['fmt_fcr']=df['timeval_fcr'].map( str )
    df['fmt_resolved']=df['resolutiondate'].map( resolved_time )
    df['fmt_timediff']=df['timeval_diff'].map( str )
    df['fmt_unattended']=df['timeval_unattended'].map( str )
    df['Tramo Duracion']=df['timeval_diff'].map( classify_duration )
    df['Duracion']=df['timeval_diff'].map( get_duration )
    df['Sin Actualizar']=df['timeval_unattended'].map( get_duration )
    df['Actualizacion OK']=df['timeval_unattended'].map( get_sla_is_attended )
    if False:
     df['Segmento Cliente']=''
     df['Averia/Config']=''
     df['Averia/Config']=df.apply( set_workdone, axis=1 )
     df['Sistema Origen']='jira'
     df['url_issue']=df['key'].map( url_ticket )
     df['Servicio Agrupado']=df[label_tecnologia].map( get_service_grouped )
     df['ServiceLine']=df[label_dpto_destino].map( set_support_level )
     df['JIRA-Tipo Ticket Incidencia']=df['Tipo Ticket Incidencia']
     df['JIRA-Tipo Ticket Reclamacion']=df['Tipo Ticket Reclamacion']
     df['JIRA-Tipo Ticket Solicitud']=df['Tipo Ticket Solicitud']
     df['JIRA-Tecnologia (Servicio)']=df[label_tecnologia]
     df['fmt_canal']=df['reporter'].map( get_canal )
     df['fmt_excepciones']=df['Nombre de cliente'].map( check_excepciones )

     for index, row in df.iterrows():
      # ---------------------
      if row['issuetype'] == 'Incidencia':
        if row['issuetype'].lower() == "incidencia" and "config" in row['Averia/Config'].lower():
          row['issuetype'] = "Solicitud"
        #***** ATENCION POSIBLE PUNTO DE FALLO DE DATOS ********
        #implementar el else:
        #***** ATENCION POSIBLE PUNTO DE FALLO DE DATOS ********

        tipo_inc = row['Tipo Ticket Incidencia']
        tecno    = row[label_tecnologia]
        problem  = ''
        #print("--> {} incidencia --> tecno:{}, tipo_inc:{}".format(index,tecno,tipo_inc))
        if tecno == '':
          tecno = tipo_inc
        elif tipo_inc == '':
          tipo_inc = tecno
        # En cualquier caso, si no hay tipo_inc, buscamos alguno patrones
        if tipo_inc == '':
          resumen = row['summary'].lower()
          if 'movil' in resumen:
            tipo_inc = 'MOVIL'
        #print("-->    PASO 1: tipo_inc:{}, tecno:{}, problem:{}".format(tipo_inc,tecno,problem))

        tecno2="" if not tecno else str(tecno) if not '-' in str(tecno) else str(tecno).split('-')[0].strip()
        problem="" if not tecno or not '-' in str(tecno) else str(tecno).split('-')[1].strip()
        x = str(tipo_inc)
        df.loc[index,'Tipo Ticket Incidencia']='' if not x else x if not '-' in x else x.split('-')[0].strip()
        df.loc[index,label_tecnologia]=tecno2
        df.loc[index,'Problema reportado']=problem
        #print("-->    PASO 2: tipo_inc:{}, tecno:{}, problem:{}".format(tipo_inc,tecno2,problem))
      # ---------------------
      elif row['issuetype'] == 'Reclamacion':
        x=str(row['Tipo Ticket Reclamacion'])
        #print("--> {} reclamacion : {}:{}".format(index,row['Tipo Ticket Reclamacion'],x))
        df.loc[index,'Tipo Ticket Reclamacion']='' if not x else x if not '-' in x else x.split('-')[0].strip()
        df.loc[index,'Problema reportado']='' if not x or not '-' in str(x) else str(x).split('-')[1].strip()
        #print( "{} //// {}".format( row['Tipo Ticket Reclamacion'], row['Problema reportado'] ))
      # ---------------------
      elif row['issuetype'] == 'Solicitud':
        x=str(row['Tipo Ticket Solicitud'])
        #print("--> {} solicitud : {}:{}".format(index,row['Tipo Ticket Solicitud'],x))
        df.loc[index,'Tipo Ticket Solicitud']='' if not x else x if not '-' in x else x.split('-')[0].strip()
        df.loc[index,'Problema reportado']='' if not x or not '-' in str(x) else str(x).split('-')[1].strip()
        #print( "{} //// {}".format( row['Tipo Ticket Solicitud'], row['Problema reportado'] ))
     # ---------------------------------------------
     df['Tipo Ticket Incidencia']=df[label_tecnologia].map( adjust_tipo_inc )

     # ====================================================================
     # SMART PROCESSING !!!
     # ====================================================================
     for index, row in df.iterrows():
      txt = row['summary'].lower()
      # ---------------------
      # STEP 1: QUALIFY RIGHT TYPE OF ISSUE
      # ---------------------
      if row['issuetype'] == 'Incidencia':
        if 'reclama' in txt:
          df.loc[index,'issuetype'] = '**Reclamacion'
        elif 'factur' in txt:
          df.loc[index,'issuetype'] = '**Reclamacion'
        elif 'solic' in txt:
          df.loc[index,'issuetype'] = '**Solicitud'
        elif 'baja' in txt:
          df.loc[index,'issuetype'] = '**Solicitud'
        elif 'cancela' in txt:
          df.loc[index,'issuetype'] = '**Solicitud'
        elif 'info' in txt:
          df.loc[index,'issuetype'] = '**Solicitud'
      # ---------------------
      # STEP 2: FOR INCIDENTS, QUALIFY CAUSE
      # ---------------------
      if row['issuetype'] == 'Incidencia' and row['Tipo Ticket Incidencia']=='':
        if any(word in txt for word in ['adsl', 'portab']):
          df.loc[index,'Tipo Ticket Incidencia']='**DATOS'
          df.loc[index,label_tecnologia]='**ADSL'
        elif 'amlt' in txt:
          df.loc[index,'Tipo Ticket Incidencia']='**VOZ'
          df.loc[index,label_tecnologia]='**AMLT'
        elif 'movil' in txt:
          df.loc[index,'Tipo Ticket Incidencia']='**MOVIL'
          df.loc[index,label_tecnologia]='**MOVIL'
        elif 'dominio' in txt:
          df.loc[index,'Tipo Ticket Incidencia']='**OTROS'
          df.loc[index,label_tecnologia]='**CLOUD'
        elif any(word in txt for word in ['pbx', 'centralita', 'extensi']):
          df.loc[index,'Tipo Ticket Incidencia']='**VOZ'
          df.loc[index,label_tecnologia]='**MERCURIO'
        elif any(word in txt for word in ['voz', 'llama', 'emite', 'escucha']):
          df.loc[index,'Tipo Ticket Incidencia']='**VOZ'
          df.loc[index,label_tecnologia]='**VOZ'
        elif 'corre' in txt:
          df.loc[index,'Tipo Ticket Incidencia']='**OTROS'
          df.loc[index,label_tecnologia]='**EMAIL'

# ------------------------------------------------------------------
def jira_extract_and_translate_columns(df):
    trans={
        'issuetype':'Tipo de Incidencia',
        'key':'Clave',
        'summary':'Resumen',
        'assignee':'Responsable',
        'reporter':'Informador',
        'priority':'Prioridad',
        'status':'Estado',
        'resolution':'Resolucion',
        'fmt_created':'Creada',
        'fmt_updated':'Actualizada',
        label_dpto_destino:label_dpto_destino,
        label_dpto_origen:label_dpto_origen,
        'resolutiondate':'Resuelta',
        'Identificador de Cliente':'Identificador de Cliente',
        'Tipo Cliente':'Tipo Cliente',
        'Nombre de cliente':'Nombre de cliente',
        'Tipo (Severidad)':'Tipo (Severidad)',
        'Tipo Ticket Incidencia':'Tipo Ticket Incidencia',
        'Tipo Ticket Reclamacion':'Tipo Ticket Reclamacion',
        'Tipo Ticket Solicitud':'Tipo Ticket Solicitud',
        label_tecnologia:label_tecnologia,
        'Segmento Cliente':'Segmento Cliente',
        'Duracion':'Duracion',
        'Tramo Duracion':'Tramo Duracion',
        'Servicio Agrupado':'Servicio Agrupado',
        'Averia/Config': 'Averia/Config',
        'Sin Actualizar': 'Sin Actualizar',
        'Actualizacion OK': 'Actualizacion OK',
        'Problema reportado': 'Problema reportado',
        'Sistema Origen': 'Sistema Origen',
        'url_issue': 'url_issue',
        'fmt_timediff':'fmt_timediff',
        'fmt_unattended':'fmt_unattended',
        'fcr':'fcr',
        'fmt_fcr':'fmt_fcr',
        'ServiceLine':'ServiceLine',
        'jira_parent':'jira_parent',
        'jira_parent_type':'jira_parent_type',
        'jira_parent_relation':'jira_parent_relation',
        'fmt_canal':'fmt_canal',
        'fmt_excepciones':'fmt_excepciones'
    }
    order=[
        'issuetype',
        'key',
        'summary',
        'assignee',
        'reporter',
        'priority',
        'status',
        'resolution',
        'fmt_created',
        'fmt_updated',
        label_dpto_destino,
        label_dpto_origen,
        'resolutiondate',
        'Identificador de Cliente',
        'Tipo Cliente',
        'Nombre de cliente',
        'Tipo (Severidad)',
        'Tipo Ticket Incidencia',
        'Tipo Ticket Reclamacion',
        'Tipo Ticket Solicitud',
        label_tecnologia,
        'Segmento Cliente',
        'Duracion',
        'Tramo Duracion',
        'Servicio Agrupado',
        'Averia/Config',
        'Sin Actualizar',
        'Actualizacion OK',
        'Problema reportado',
        'Sistema Origen',
        'url_issue',
        'fmt_timediff',
        'fmt_unattended',
        'fmt_fcr',
        'fcr',
        'ServiceLine',
        'jira_parent',
        'jira_parent_type',
        'jira_parent_relation',
        'fmt_canal',
        'fmt_excepciones'
    ]
    print("* Filtering and processing report columns")
    #print("* Extracting columns:"+str(order))
    #df = df.reset_index()
    df1=pd.DataFrame( df, columns=order )
    cols2=[]
    for i in order:
        cols2.append( trans[i] )
    #print("* Translating columns:"+str(cols2))
    #print( df1.columns )
    df1.columns= cols2 
    return df1

# ------------------------------------------------------------------
def jira_query(title,item):
    # Get first response for headers: get total number of records
    # {"expand":"schema,names","startAt":0,"maxResults":50,"total":445503,"issues"
    issues=[]
    rows=1000
    startAt=0
    total=1
    url_opts=''

    print( "---------------------------\nJIRA: retrieving "+title)
    while( startAt < total ):
        print( "   --> total:{}, startAt:{}, maxResults:{}".format( total, startAt, rows ))
        # -- Do query --
        url_opts="startAt={}&maxResults={}&".format( startAt, rows )
        url=opts['jira_url_api']+'/search?'+url_opts+"jql="+item["query"]
        response = requests.get(url, auth=(opts['jira_user'], opts['jira_passw']))
        print( response )
        if response.status_code != 200:
            print("   --> ERROR:", str(response))
            return issues
        jresp = json.loads(response.text)
        curr_rows=len(jresp['issues'])
        total=jresp['total']
        flag_continue=True
        for i in jresp['issues']:
            if flag_continue:
                t = jira_translate_ticket(i)
                issues.append(t)
                #flag_continue=False
        print( "   --> GOT {} / {}  records".format(len(jresp['issues']), jresp['total']))
        startAt += curr_rows
    # df = pd.DataFrame(issues,index=['key'])
    df = pd.DataFrame(issues)
    # df = pd.DataFrame(issues)
    jira_replace_headers(df)
    if flag_dump_raw:
        print( "* Dumping to raw data file:" + item["raw"])
        df.to_csv(item["raw"]+"_raw1.csv", sep=';')
    jira_calculate_columns(df)
    if flag_dump_raw:
        print( "* Dumping to raw-translated data file:" + item["raw"])
        df.to_csv(item["raw"]+"_raw2.csv", sep=';')

    if flag_extract_and_translate:
      df1 = jira_extract_and_translate_columns(df)
      print( "* Dumping to filtered file:" + item["file"])
      # df.to_csv(out_file, sep=';', encoding='utf-8')
      df1.to_csv(item["file"]+".csv", sep=';')

    print( "* Done\n" )
    return issues

# ------------------------------------------------------------------
def generate_report(prefix, raw_prefix, from_date, to_date):
    #start_date=''
    #end_date=start_date+7
    
    jira_get_fields()
    
    queries_jira= {}

    if flag_get_masivas_red:
      queries_jira['MASIVAS / RED / OPENED FROM DATE']={
        "file": "{}_IDR_opened_from_date".format(prefix),
        "raw": "{}_IDR_opened_from_date".format(raw_prefix),
        "query": 'project = "Incidencias de Red" AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

    if flag_get_masivas_sist:
      queries_jira['MASIVAS / SISTEMAS / OPENED FROM DATE']={
        "file": "{}_IMS_opened_from_date".format(prefix),
        "raw": "{}_IMS_opened_from_date".format(raw_prefix),
        "query": 'project = "Incidencias Masivas" AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

#    if False:
#      queries_jira['MASEMP / INCIDENCIAS RED']={
#        "file": "{}_b2b_jira_Q4_REDES".format(prefix),
#        "raw": "{}_b2b_jira_Q4_REDES".format(raw_prefix),
#        "query": 'project = MASEMP AND departamento = "Departamento Red" AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}
#      queries_jira['MASEMP / INCIDENCIAS RED']={
#        "file": "{}_b2b_jira_ano_2016".format(prefix),
#        "raw": "{}_b2b_jira_ano_2016".format(raw_prefix),
#        "query": 'project = MASEMP AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

    for i in queries_jira:
        issues = jira_query(i, queries_jira[i])

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

  opts['jira_url_api']="https://jira.masmovil.com/rest/api/2"
  opts['jira_user']="alvaro.paricio"
  opts['jira_passw']="masmovil2017"

  print("*** Collect from date: {}".format(opts['from_date']))
  print("*** Collect to   date: {}".format(opts['to_date']))

  return opts

# ------------------------------------------------------------------
opts = getConfig()
now=datetime.now()
prefix='{}/JIRA_{}_{}{}'.format(
				opts['out_dir'],
				opts['pp_from_date'],
				opts['pp_to_date'],
				opts['pp_hour']
				)
raw_prefix='{}/JIRA_{}_{}{}'.format(
				opts['raw_dir'],
				opts['pp_from_date'],
				opts['pp_to_date'],
				opts['pp_hour']
				)
issues = generate_report(prefix,raw_prefix,opts['from_date'], opts['to_date'])

