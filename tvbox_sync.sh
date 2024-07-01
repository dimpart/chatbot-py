#!/usr/bin/env bash

logs=/tmp

time=$(date +%Y%m%d-%H%M%S)

# start "name" "python_command" "arguments"
function start() {
    res=$(pgrep -f "$2 $3")
    if [[ "${res}" == "" ]]
    then
        log=${logs}/$1-${time}.log
        echo "!!! starting $2 $3 >> ${log}"
        "$2" $3 >> "${log}" 2>&1 &
    else
        for pid in ${res[*]}
        do
            echo "!!! process exists: $2 $3 ($((pid)))"
        done
    fi
}

function title() {
    echo ""
    echo "    >>> $1 <<<"
    echo ""
}

function finish() {
    echo ""
    echo "    >>> Done <<<"
    echo ""
}


#
#   main
#

title "TVBox Syncing"
start tvbox-sync "tvbox" "sync lives"

finish
