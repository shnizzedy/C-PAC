#!/bin/bash

### Takes a runscript and a participant number as positional variables

EXIT_STATUS=1
while read OUT
do
  echo "$OUT"
  if [[ "$OUT" =~ .*"run complete".* ]]; then
    EXIT_STATUS=0
  fi
done <<<$($1 $2);
exit $EXIT_STATUS