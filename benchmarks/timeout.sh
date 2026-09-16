#!/bin/zsh
# timeout(1) n'existe pas sur macOS : équivalent minimal.
# usage : timeout.sh <secondes> <commande...>
limit=$1; shift
"$@" &
pid=$!
( sleep "$limit"; kill -9 $pid 2>/dev/null ) &
watcher=$!
wait $pid 2>/dev/null; code=$?
kill -9 $watcher 2>/dev/null
exit $code
