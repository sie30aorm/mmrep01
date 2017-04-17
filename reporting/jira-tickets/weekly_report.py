#=====================================================================
# REPORITNG FROM JIRA
#=====================================================================
# Author: Alvaro Paricio
#=====================================================================
import pandas as pd
import requests
import re
import json
import pprint
from requests.auth import HTTPBasicAuth
from datetime import datetime

jira_req_data=""
jira_struct={}

opts={}
flag_verbose=False
flag_dump_raw=False

pp = pprint.PrettyPrinter(indent=3)

# ------------------------------------------------------------------
def jira_get_fields():
    global jira_struct
    # {'custom': True,
    # 'clauseNames': ['cf[10500]', 'Flag Notificación No Validez del Cierre'], 'name': 'Flag Notificación No Validez del Cierre', 'orderable': True, 'schema': {'customId': 10500, 'custom': 'com.atlassian.jira.plugin.system.customfieldtypes:textfield', 'type': 'string'}, 'searchable': True, 'navigable': True, 'id': 'customfield_10500'}    url_opts=''
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
        #print(str(f_id)+" -->  "+f_name)
    print( "Done\n" )

# ------------------------------------------------------------------
def jira_translate_ticket(issue):
    ticket={}
    ticket['id']=issue['id']
    ticket['key']=issue['key']
    for f in issue['fields']:
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
def set_open_time(row):
    timeval_created =  row['timeval_created']
    if not row['resolutiondate'] or row['resolutiondate'] == '':
        timeval_diff=datetime.now()-timeval_created
    else:
        timeval_resolutiondate = datetime.strptime(row['resolutiondate'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        timeval_diff=timeval_resolutiondate-timeval_created
    return timeval_diff

# ------------------------------------------------------------------
def jira_calculate_columns(df):
    time_value=lambda x: datetime.strptime(x.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    format_time=lambda x: datetime.strftime( x, '%d/%m/%Y %H:%M:%S' )
    classify_duration=lambda x: '<1D' if x.days < 1 else '<2D' if x.days < 2 else '<5D' if x.days < 5 else '<7D' if x.days < 7 else '>7D'
    get_duration=lambda x: "{}".format(x.days+x.seconds/86400).replace('.', ',')
    url_ticket=lambda x: "{}/{}".format( "https://jira.masmovil.com/browse/", x)
    get_duration=lambda x: "{}".format(x.days+x.seconds/86400).replace('.', ',')
    # SLA: ticket updated made in hours
    get_sla_is_attended=lambda x: 'OK' if x.days*24+x.seconds/3600 < 24 else 'KO'
    get_service_grouped=lambda x: '' if not x else str(x).split('-')[0]
    get_service_problem=lambda x: '' if not x or not '-' in str(x) else str(x).split('-')[1]
    
    now = datetime.now()
    df['timeval_created']=df['created'].map( time_value )
    df['timeval_updated']=df['updated'].map( time_value )
    # df['timeval_diff']=df['timeval_updated']-df['timeval_created']
    df['timeval_diff']=df.apply( set_open_time, axis=1 )
    df['timeval_unattended']=now - df['timeval_updated']

    df['fmt_created']=df['timeval_created'].map( format_time )
    df['fmt_updated']=df['timeval_updated'].map( format_time )
    df['fmt_timediff']=df['timeval_diff'].map( str )
    df['fmt_unattended']=df['timeval_unattended'].map( str )
    df['Tramo Duracion']=df['timeval_diff'].map( classify_duration )
    df['Duracion']=df['timeval_diff'].map( get_duration )
    df['Sin Actualizar']=df['timeval_unattended'].map( get_duration )
    df['Actualizacion OK']=df['timeval_unattended'].map( get_sla_is_attended )
    df['Segmento Cliente']=''
    df['Averia/Config']=''
    df['Averia/Config']=df.apply( set_workdone, axis=1 )
    df['Sistema Origen']='jira'
    df['url_issue']=df['key'].map( url_ticket )
    df['Servicio Agrupado']=df['Tecnologia (Servicio)'].map( get_service_grouped )
    df['Problema reportado']=df['Tecnologia (Servicio)'].map( get_service_problem )

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
        'resolution':'Resolución',
        'fmt_created':'Creada',
        'fmt_updated':'Actualizada',
        'Departamento':'Departamento',
        'Departamento Origen':'Departamento Origen',
        'resolutiondate':'Resuelta',
        'Identificador de Cliente':'Identificador de Cliente',
        'Tipo Cliente':'Tipo Cliente',
        'Nombre de cliente':'Nombre de cliente',
        'Tipo (Severidad)':'Tipo (Severidad)',
        'Tipo Ticket Incidencia':'Tipo Ticket Incidencia',
        'Tipo Ticket Reclamacion':'Tipo Ticket Reclamacion',
        'Tipo Ticket Solicitud':'Tipo Ticket Solicitud',
        'Tecnologia (Servicio)':'Tecnologia (Servicio)',
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
        'fmt_unattended':'fmt_unattended'
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
        'Departamento',
        'Departamento Origen',
        'resolutiondate',
        'Identificador de Cliente',
        'Tipo Cliente',
        'Nombre de cliente',
        'Tipo (Severidad)',
        'Tipo Ticket Incidencia',
        'Tipo Ticket Reclamacion',
        'Tipo Ticket Solicitud',
        'Tecnologia (Servicio)',
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
        'fmt_unattended'
    ]
    print("* Filtering and processing report columns")
    #print("* Extracting columns:"+str(order))
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
    df = pd.DataFrame(issues)
    jira_replace_headers(df)
    jira_calculate_columns(df)
    if flag_dump_raw:
        print( "* Dumping to raw data file:" + item["file"])
        df.to_csv(item["file"]+".raw.csv", sep=';')

    df1 = jira_extract_and_translate_columns(df)
    print( "* Dumping to filtered file:" + item["file"])
    # df.to_csv(out_file, sep=';', encoding='utf-8')
    df1.to_csv(item["file"]+".csv", sep=';')
    print( "* Done\n" )
    return issues

# ------------------------------------------------------------------
def generate_report(prefix, from_date, to_date):
    #start_date=''
    #end_date=start_date+7
    
    jira_get_fields()
    
    queries_jira= {}
    #queries_jira['MASEMP / SOLICITUDES / ABIERTAS']={"file": "b2b_jira_solic_open", "query": 'project = MASEMP AND issuetype = "Incidencia Cliente" AND status in (CREADA, "In Progress") ORDER BY createdDate DESC, resolution DESC'}
    #queries_jira['MASEMP / RECLAMACIONES / ABIERTAS']={"file": "b2b_jira_reclam_open", "query": 'project = MASEMP AND issuetype = Reclamacion AND status in (CREADA, "In Progress") ORDER BY createdDate DESC, resolution DESC'}
    #queries_jira['MASEMP / INCIDENCIAS / ABIERTAS']={"file": "b2b_jira_incid_open", "query": 'project = MASEMP AND issuetype = Solicitud AND status in (CREADA, "In Progress") ORDER BY createdDate DESC, resolution DESC'}
    
    if False:
        queries_jira['MASEMP / TODAS / ABIERTAS']={"file": "{}_b2b_jira_all_currently_open".format(prefix), "query": 'project = MASEMP AND status in (CREADA, "In Progress") ORDER BY createdDate DESC, resolution DESC'}
        queries_jira['MASEMP / TODAS / OPEN_WEEK']={"file": "{}_b2b_jira_all_weekly_open".format(prefix), "query": 'project = MASEMP AND issuetype in standardIssueTypes() AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}
        queries_jira['MASEMP / TODAS / CLOSED_WEEK']={"file": "{}_b2b_jira_weekly_closed".format(prefix), "query": 'project = MASEMP AND issuetype in standardIssueTypes() AND resolved >= {} AND resolved <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

    if True:
        queries_jira['MASEMP / TODAS / ABIERTAS']={"file": "{}_b2b_jira_currently_open".format(prefix), "query": 'project = MASEMP AND status in (CREADA, "In Progress") ORDER BY createdDate DESC, resolution DESC'}
        queries_jira['MASEMP / TODAS / OPEN FROM 16/01']={"file": "{}_b2b_jira_open_from_date".format(prefix), "query": 'project = MASEMP AND issuetype in standardIssueTypes() AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}
        queries_jira['MASEMP / TODAS / CLOSED FROM 16/01']={"file": "{}_b2b_jira_closed_from_date".format(prefix), "query": 'project = MASEMP AND issuetype in standardIssueTypes() AND resolved >= {} AND resolved <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

    #queries_jira['MASEMP / INCIDENCIAS RED']={"file": "{}_b2b_jira_Q4_REDES".format(prefix), "query": 'project = MASEMP AND departamento = "Departamento Red" AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}
    #queries_jira['MASEMP / INCIDENCIAS RED']={"file": "{}_b2b_jira_ano_2016".format(prefix), "query": 'project = MASEMP AND created >= {} AND created <= {} ORDER BY createdDate DESC, resolution DESC'.format(from_date, to_date)}

    for i in queries_jira:
        issues = jira_query(i, queries_jira[i])
    
# ------------------------------------------------------------------
def getConfig():
  opts={}
  opts['out_dir']='.'
  opts['from_date']='2017-01-16'
  now=datetime.now()
  opts['to_date']=datetime.strftime( now, '%Y-%m-%d' )
  opts['jira_url_api']="https://jira.masmovil.com/rest/api/2"
  opts['jira_user']="alvaro.paricio"
  opts['jira_passw']="masmovil2017"
  return opts

# ------------------------------------------------------------------
opts = getConfig()
opts['to_date']='2017-02-02'
now=datetime.now()
prefix='{}/JIRA_{}_from_{}'.format(	opts['out_dir'],
				datetime.strftime( now, '%Y-%m-%d-%H'),
				opts['from_date']
				)
issues = generate_report(prefix,opts['from_date'], opts['to_date'])

