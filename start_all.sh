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

title "DIM Chat Bots"
restart ling "bots/chatbot_ling.py"
restart xiao "bots/chatbot_xiao.py"

title "DIM Chat Room"
restart chatroom "bots/chatroom_admin.py"

title "DIM Group Assistant"
restart group "bots/gbot_assistant.py"

echo ""
echo "    >>> Done <<<"
echo ""
