#/bin/bash
# python -m SimpleHTTPServer 3000
LOG_PATH="`pwd`/log"
LOGNAME="${LOG_PATH}/server.log"
DATA_DIR="/reports/jira/daily"

mkdir ${LOG_PATH} 2>/dev/null
cd ${DATA_DIR}
python3 -m http.server 3000 > ${LOGNAME} 2>&1
