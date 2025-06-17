#!/usr/bin/env bash

root=$(cd "$(dirname "$0")" || exit;pwd)

start_shell=${root}/shell_start.sh
stop_shell=${root}/shell_stop.sh

# start "name" "path/to/script.py"
function start() {
    ${start_shell} "$1" "${root}/$2"
}

# stop "path/to/script.py"
function stop() {
    ${stop_shell} "${root}/$1"
}

# restart "name" "path/to/script.py"
function restart() {
    stop "$2"
    sleep 1
    start "$1" "$2"
}

function title() {
    echo ""
    echo "    >>> $1 <<<"
    echo ""
}


if [[ "$*" == "restart" ]]
then
    launch="restart"
    echo "========================"
    echo "    Restarting ..."
    echo "========================"
else
    launch="start"
    echo "========================"
    echo "    Starting ..."
    echo "========================"
fi


#
#   Service Bots
#

title "DIM Chat Bots"
${launch} gege "bots/chatbot_gemini.py"
${launch} gigi "bots/chatbot_gpt.py"

title "DIM Search Bots"
${launch} simon "bots/sebot_sm.py"

echo ""
echo "    >>> Done <<<"
echo ""
