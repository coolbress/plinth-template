#!/usr/bin/env bash
# Runs a heavy command, such as the whole test suite, when one of this
# machine's slots is free, and waits otherwise:
#
#   scripts/heavy.sh uv run pytest
#
# The slots are the machine's, not this repository's: every project made
# with plinth shares one directory under ${TMPDIR:-/tmp}.
# It holds one entry per running command, named by its pid; an entry whose
# pid is gone is taken back. No flock: macOS has none. Written for bash 3.2.
#
#   PLINTH_HEAVY_SLOTS  how many run at once (default 2; set 1 on a small
#                       machine)
#   PLINTH_HEAVY_WAIT   minutes to wait for a slot (default 20). Then the
#                       command does not run and the exit status is 75:
#                       report that check as not verified, never as passed.
#
# While it waits it prints, once a minute, how many run and their pids.
set -u

if [ "$#" -eq 0 ]; then
  echo "usage: scripts/heavy.sh <command> [<argument>...]" >&2
  exit 2
fi
slots=${PLINTH_HEAVY_SLOTS:-2}
limit=${PLINTH_HEAVY_WAIT:-20}
case "$slots" in
  '' | *[!0-9]* | 0)
    echo "heavy.sh: PLINTH_HEAVY_SLOTS is '$slots'; it takes a whole number from 1" >&2
    exit 2
    ;;
esac
case "$limit" in
  '' | *[!0-9]*)
    echo "heavy.sh: PLINTH_HEAVY_WAIT is '$limit'; it takes a whole number of minutes" >&2
    exit 2
    ;;
esac

tmp=${TMPDIR:-/tmp}
queue="${tmp%/}/plinth-heavy-$(id -u)"
mkdir -p -m 700 "$queue" || exit 2
# Another user can make this path first, on a shared /tmp, and fill it with
# links to this user's files for the entry's write to overwrite.
if [ -L "$queue" ] || [ ! -O "$queue" ]; then
  echo "heavy.sh: $queue is a link or not this user's; remove it, then run again" >&2
  exit 2
fi
# Without ps every entry, this one's too, reads as gone: no limit, no word.
if ! ps -p $$ >/dev/null 2>&1; then
  echo "heavy.sh: ps cannot see this process here, so the slots cannot be counted; run the command without scripts/heavy.sh" >&2
  exit 2
fi

# The pids of the commands running now; a dead one's entry is removed.
# `ps -p`, not `kill -0`: a live process the caller may not signal, as a
# sandbox can make another session's be, fails `kill -0` like a dead one.
running() {
  for entry in "$queue"/*; do
    [ -e "$entry" ] || continue
    pid=${entry##*/}
    if ps -p "$pid" >/dev/null 2>&1; then
      printf '%s ' "$pid"
    else
      rm -f "$entry"
    fi
  done
}

me=$$
began=$SECONDS
told=''
while :; do
  # Take an entry first and count after, so two callers that arrive together
  # both count each other and neither runs over the limit.
  printf '%s\n' "$me" >"$queue/$me"
  pids=$(running)
  n=0
  for pid in $pids; do n=$((n + 1)); done
  if [ "$n" -le "$slots" ]; then
    # The command keeps this pid, so its entry is live exactly while it runs.
    exec "$@"
  fi
  rm -f "$queue/$me"
  others=$(printf '%s' "$pids" | tr ' ' '\n' | grep -vx "$me" | tr '\n' ' ')
  others=${others% }
  waited=$((SECONDS - began))
  if [ "$waited" -ge $((limit * 60)) ]; then
    echo "heavy.sh: did not run '$*': all $slots slots were busy for $limit minutes (pids $others). Report it as not verified." >&2
    exit 75
  fi
  if [ -z "$told" ] || [ $((SECONDS - told)) -ge 60 ]; then
    echo "heavy.sh: waiting for a slot: $((n - 1)) running (pids $others), PLINTH_HEAVY_SLOTS=$slots; waited $((waited / 60)) of $limit minutes" >&2
    told=$SECONDS
  fi
  sleep "1.$((RANDOM % 10))"
done
