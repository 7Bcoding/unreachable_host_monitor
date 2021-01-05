#!/bin/bash

function main() {
  unreachable_hostlist_file="xxx/unreachable_monitor/file/unreachable_file"
  cd /home/cloud_op_local/cenquanyu/snic_bbc_unreachable_monitor/ && sudo /xxx/venv/venv_python36/bin/python3 snic_bbc_unreachable_monitor.py > "${unreachable_hostlist_file}"
  unreachable_host=$(cat "${unreachable_hostlist_file}" | grep unreachable_host | awk '{print $2}')
  if [ ! $unreachable_host ];then
    echo unreachable_host:'NULL'
  else
    echo unreachable_host:\"${unreachable_host}\"
  fi
}

main "$@"
