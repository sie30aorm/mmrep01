#/bin/bash
# python -m SimpleHTTPServer 3000
MYPWD=`pwd`
LOG_PATH="${MYPWD}/log"
LOGNAME="${LOG_PATH}/server.log"
DATA_DIR="/reports/public"

set -x
mkdir ${LOG_PATH} 2>/dev/null
cd ${DATA_DIR}
python3 ${MYPWD}/server.py > ${LOGNAME} 2>&1 &
