#/bin/bash

PROG="DEMANDA"

EXE_PATH="/home/reports/production/reporting/jira-tickets"
PY_EXE="${PROG}.py"

PY="/usr/bin/python"
CMD="${PY} ${EXE_PATH}/${PY_EXE} $*"
echo "======================================================"
echo "          DUMPING JIRA DAILY REPORTS"
date
echo "======================================================"
set -x
${CMD}

