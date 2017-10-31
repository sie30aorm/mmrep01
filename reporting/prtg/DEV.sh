#/bin/bash

PROG="DEV"

EXE_PATH="/home/reports/workspace/reporting/prtg"
PY_EXE="${PROG}.py"

PY="/usr/bin/python"
CMD="${PY} ${EXE_PATH}/${PY_EXE} $*"
echo "======================================================"
echo "          DUMPING JIRA DAILY REPORTS"
date
echo "======================================================"
set -x
${CMD}

