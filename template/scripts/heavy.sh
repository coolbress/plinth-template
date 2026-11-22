#!/usr/bin/env bash
# Runs a heavy command, such as the whole test suite, when one of this
# machine's slots is free, and waits otherwise:
#
#   scripts/heavy.sh uv run pytest
#
# The queue is per TMPDIR: every project made with plinth whose sessions see
# the same ${TMPDIR:-/tmp} shares one directory there. A session whose TMPDIR
# differs, as a sandboxed one's can, has a queue of its own and does not wait
# for this one's commands.
#
# Waiters are served in the order they arrived. Each takes a numbered ticket
# holding its pid; the oldest PLINTH_HEAVY_SLOTS live tickets run, and a
# ticket whose pid is gone, killed or ended, is dropped. No flock: macOS has
# none. Written for bash 3.2.
#
#   PLINTH_HEAVY_SLOTS  how many run at once (default 2; set 1 on a small
#                       machine)
#   PLINTH_HEAVY_WAIT   minutes to wait for a slot (default 20). Then the
#                       command does not run and the exit status is 75:
#                       report that check as not verified, never as passed.
#
# While it waits it prints, once a minute, how many wait ahead of it, what
# runs and for how long. A waiter that watched a command end remembers how
# long it ran; when even the shortest of the last five puts the wait past
# PLINTH_HEAVY_WAIT, it exits 75 at once instead of waiting it out.
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
# Tickets live in a hidden directory: an older heavy.sh, from a project not
# yet updated, removes every file in $queue whose name is not a live pid,
# and its glob skips a name that starts with a dot.
tickets="$queue/.tickets"
mkdir -m 700 "$tickets" 2>/dev/null || [ -d "$tickets" ] || exit 2
if [ -L "$tickets" ]; then
  echo "heavy.sh: $tickets is a link; remove it, then run again" >&2
  exit 2
fi
took="$tickets/.took"

me=$$
arrived=$(date +%s)
mine=''
new="$tickets/.new.$me"
trap 'rm -f "$new" ${mine:+"$mine"}; exit 130' INT
trap 'rm -f "$new" ${mine:+"$mine"}; exit 143' TERM
trap 'rm -f "$new" ${mine:+"$mine"}; exit 129' HUP

# The next number after the highest live ticket. `ln` makes the name only if
# no other waiter made it first, with its content already in place, so there
# is no lock to leave behind when a waiter is killed.
take() {
  printf '%s %s\n' "$me" "$arrived" >"$new" || exit 2
  tries=0
  while :; do
    last=0
    for t in "$tickets"/[0-9]*; do
      case "${t##*/}" in *[!0-9]*) continue ;; esac
      if [ -e "$t" ] || [ -L "$t" ]; then last=${t##*/}; fi
    done
    mine=$(printf '%s/%010d' "$tickets" $((10#$last + 1)))
    ln "$new" "$mine" 2>/dev/null && break
    tries=$((tries + 1))
    if [ "$tries" -ge 50 ]; then
      rm -f "$new"
      echo "heavy.sh: could not take a ticket in $tickets; remove that directory, then run again" >&2
      exit 2
    fi
  done
  rm -f "$new"
}

# Reads the queue. Sets: place (-1 when this waiter has no ticket), ahead
# (tickets before this one still waiting), busy (how many run), what (their
# pids and ages), ages (seconds each running one has run, one per line). A
# dead ticket is dropped. One that this waiter saw running at its last scan
# leaves how long it ran, to within one poll: a command that ended unwatched
# leaves nothing, since the time until the next call is not its run time.
seen=' '
scan() {
  now=$(date +%s)
  place=-1 ahead=0 busy=0 what='' ages='' live=" $me " watched=' '
  for t in "$tickets"/[0-9]* "$tickets"/.new.*; do
    case "${t##*/}" in .new.*) ;; *[!0-9]*) continue ;; esac
    [ -e "$t" ] || continue
    { read -r pid _ started; } <"$t" 2>/dev/null || continue
    if [ "$t" = "$mine" ]; then
      place=1
      continue
    fi
    if ! ps -p "$pid" >/dev/null 2>&1; then
      if rm "$t" 2>/dev/null && [ -n "${started:-}" ]; then
        case "$seen" in *" $pid "*) printf '%s\n' $((now - started)) >>"$took" ;; esac
      fi
      continue
    fi
    case "$t" in */.new.*) continue ;; esac
    live="$live$pid "
    if [ -n "${started:-}" ]; then
      watched="$watched$pid "
      busy=$((busy + 1))
      what="$what, pid $pid for $(((now - started) / 60)) min"
      ages="$ages$((now - started))
"
    elif [ "$place" -lt 0 ]; then
      ahead=$((ahead + 1))
    fi
  done
  # An older heavy.sh's entries, named by their pid: each holds a slot. The
  # entry this script writes for an older one to count is its ticket's pid.
  for e in "$queue"/[0-9]*; do
    [ -f "$e" ] || continue
    pid=${e##*/}
    case "$live" in *" $pid "*) continue ;; esac
    if ps -p "$pid" >/dev/null 2>&1; then
      busy=$((busy + 1))
      what="$what, pid $pid"
      ages="${ages}0
"
    else
      rm -f "$e"
    fi
  done
  what=${what#, }
  seen=$watched
}

# The wait this waiter can estimate, in seconds, from the shortest of the
# last five runs: each running command takes that long in all, and each
# waiter ahead takes that long again on the first slot to come free. Empty
# when no run is remembered yet.
estimate() {
  wait='' shortest=''
  [ -f "$took" ] || return 0
  for d in $(tail -n 5 "$took"); do
    case "$d" in '' | *[!0-9]*) continue ;; esac
    if [ -z "$shortest" ] || [ "$d" -lt "$shortest" ]; then shortest=$d; fi
  done
  [ -n "$shortest" ] || return 0
  # When each slot comes free: a running command's time left, 0 for a free
  # slot. With more running than slots, the first to end free none.
  frees=$(
    {
      printf '%s' "$ages" | while read -r age; do
        r=$((shortest - age))
        [ "$r" -gt 0 ] || r=0
        echo "$r"
      done
      i=$busy
      while [ "$i" -lt "$slots" ]; do
        echo 0
        i=$((i + 1))
      done
    } | sort -n | tail -n "$slots"
  )
  i=0
  while [ "$i" -lt "$ahead" ]; do
    first=${frees%%[!0-9]*}
    frees=$({
      printf '%s\n' "$frees" | sed 1d
      echo $((first + shortest))
    } | sort -n)
    i=$((i + 1))
  done
  wait=${frees%%[!0-9]*}
}

take
began=$SECONDS
told=''
while :; do
  scan
  if [ "$place" -lt 0 ]; then
    # The ticket is gone, as when the directory was cleared: take another.
    take
    continue
  fi
  # It runs when what runs and what waits ahead of it leave a slot free.
  if [ $((ahead + busy)) -lt "$slots" ]; then
    # For an older heavy.sh, which counts only entries named by a pid: write
    # the entry first and count again, as it does, so that the two arriving
    # together cannot both miss the other.
    printf '%s\n' "$me" >"$queue/$me"
    scan
    if [ $((ahead + busy)) -lt "$slots" ]; then
      trap - INT TERM HUP
      printf '%s %s %s\n' "$me" "$arrived" "$(date +%s)" >"$new" && mv -f "$new" "$mine"
      # The command keeps this pid, so its ticket is live exactly while it runs.
      exec "$@"
    fi
    rm -f "$queue/$me"
  fi
  waited=$((SECONDS - began))
  estimate
  if [ "$waited" -ge $((limit * 60)) ]; then
    rm -f "$mine"
    echo "heavy.sh: did not run '$*': all $slots slots were busy for $limit minutes ($what). Report it as not verified." >&2
    exit 75
  fi
  if [ -n "$wait" ] && [ $((waited + wait)) -gt $((limit * 60)) ]; then
    rm -f "$mine"
    echo "heavy.sh: did not run '$*': $ahead ahead, $busy running ($what); the shortest of the last runs took $((shortest / 60)) min, so the wait is at least $(((waited + wait) / 60)) min, past PLINTH_HEAVY_WAIT=$limit. Report it as not verified." >&2
    exit 75
  fi
  if [ -z "$told" ] || [ $((SECONDS - told)) -ge 60 ]; then
    more=''
    [ -n "$wait" ] && more=", about $((wait / 60)) min more"
    echo "heavy.sh: waiting for a slot: $ahead ahead, $busy running ($what), PLINTH_HEAVY_SLOTS=$slots; waited $((waited / 60)) of $limit minutes$more" >&2
    told=$SECONDS
  fi
  sleep "1.$((RANDOM % 10))"
done
