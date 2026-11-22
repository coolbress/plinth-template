#!/usr/bin/env bash
# Runs a heavy command, such as the whole test suite, when one of this
# machine's slots is free, and waits otherwise:
#
#   scripts/heavy.sh uv run pytest
#
# The queue lives in /tmp/claude-<uid> when Claude Code made it there, as
# it does for every session, sandboxed or not; otherwise in ${TMPDIR:-/tmp}.
# PLINTH_HEAVY_DIR names another place.
#
# Waiters are served in the order they arrived. Each takes a ticket named
# <number>.<pid>.<arrival> and holds a lock on it, through perl's flock, for
# as long as it waits and its command runs. The kernel drops the lock when
# that process dies, even by kill -9, so a ticket no one holds is dropped.
# Neither ps nor a pid is read for this: a sandboxed session sees no process.
# Written for bash 3.2.
#
#   PLINTH_HEAVY_SLOTS  how many run at once (default 2; set 1 on a small
#                       machine)
#   PLINTH_HEAVY_WAIT   minutes to wait for a slot (default 20). Then the
#                       command does not run and the exit status is 75:
#                       report that check as not verified, never as passed.
#                       It is 75 as well when there is no queue to join:
#                       no perl, or no place to write.
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

cmd="$*"
cannot() {
  echo "heavy.sh: did not run '$cmd': $1, so it cannot queue. Report it as not verified." >&2
  exit 75
}
uid=$(id -u)
base=${PLINTH_HEAVY_DIR:-/tmp/claude-$uid}
if [ ! -d "$base" ] || [ -L "$base" ] || [ ! -O "$base" ]; then base=${TMPDIR:-/tmp}; fi
queue="${base%/}/plinth-heavy-$uid"
mkdir -p -m 700 "$queue" 2>/dev/null || cannot "$queue cannot be made"
# Another user can make this path first, on a shared /tmp, and fill it with
# links to this user's files for the entry's write to overwrite.
if [ -L "$queue" ] || [ ! -O "$queue" ]; then
  echo "heavy.sh: $queue is a link or not this user's; remove it, then run again" >&2
  exit 2
fi
tickets="$queue/.tickets"
mkdir -m 700 "$tickets" 2>/dev/null || [ -d "$tickets" ] || cannot "$tickets cannot be made"
if [ -L "$tickets" ]; then
  echo "heavy.sh: $tickets is a link; remove it, then run again" >&2
  exit 2
fi
took="$tickets/.took"
# An older heavy.sh keeps a file named by its pid in ${TMPDIR:-/tmp}'s
# plinth-heavy-<uid> for each command it runs, and counts only those, read
# with ps. Where ps sees this process, this one writes and counts them too.
legacy=''
if ps -p $$ >/dev/null 2>&1; then
  legacy=${TMPDIR:-/tmp}
  legacy="${legacy%/}/plinth-heavy-$uid"
  if ! mkdir -p -m 700 "$legacy" 2>/dev/null || [ -L "$legacy" ] || [ ! -O "$legacy" ]; then legacy=''; fi
fi

me=$$
arrived=$(date +%s)
mine=''
new="$tickets/.new.$me"
trap 'rm -f "$new" ${mine:+"$mine"}; exit 130' INT
trap 'rm -f "$new" ${mine:+"$mine"}; exit 143' TERM
trap 'rm -f "$new" ${mine:+"$mine"}; exit 129' HUP

# Takes the lock on fd 9 and keeps it there after perl exits: the lock
# belongs to the open file, which this shell, and the command it becomes,
# keep open. A child of the command that keeps fd 9 open keeps it too.
# shellcheck disable=SC2016 # perl code, expanded by perl
hold='use Fcntl ":flock"; open(my $f, ">&=", 9) or exit 1; flock($f, LOCK_EX | LOCK_NB) or exit 1'
# Prints each ticket's name in order, "live" or "gone", with its line; removes a
# gone one only while it holds its lock and the name is still that file, so
# a scan that read a dead ticket cannot remove a live one made since.
# shellcheck disable=SC2016
sweep='use Fcntl ":flock";
opendir(my $d, $ARGV[0]) or exit 1;
for my $n (sort readdir($d)) {
  my $t = "$ARGV[0]/$n";
  next unless $n =~ /^\d{10}\.\d{10}\.\d{10}$/ and open(my $f, "<", $t);
  my $line = <$f> // ""; chomp $line;
  if (!flock($f, LOCK_SH | LOCK_NB)) { print "live $n $line\n"; next }
  my @a = stat($f); my @b = lstat($t);
  print "gone $n $line\n" if @b and "$a[0] $a[1]" eq "$b[0] $b[1]" and unlink $t;
}'

# The next number after the highest ticket, the lock taken before the name
# is visible: a scan never sees it unheld. Two waiters can take one number;
# the pid after it orders them, the same way for every scanner.
take() {
  mine=''
  { printf '%s %s\n' "$me" "$arrived" >"$new" && exec 9>>"$new"; } 2>/dev/null || cannot "$new cannot be written"
  perl -e "$hold" 2>/dev/null || cannot "perl could not hold a lock on $new"
  last=0
  for t in "$tickets"/[0-9]*; do
    n=${t##*/}
    n=${n%%.*}
    case "$n" in '' | *[!0-9]*) continue ;; esac
    if [ $((10#$n)) -gt $((10#$last)) ]; then last=$n; fi
  done
  try=$(printf '%s/%010d.%010d.%010d' "$tickets" $((10#$last + 1)) "$me" "$arrived")
  mv "$new" "$try" || cannot "$try cannot be written"
  mine=$try
}

# Reads the queue. Sets: place (-1 when this waiter has no ticket), ahead
# (tickets before this one still waiting), busy (how many run), what (their
# pids and ages), ages (seconds each running one has run, one per line). A
# gone ticket that this waiter saw running at its last scan leaves how long
# it ran, to within one poll: a command that ended unwatched leaves nothing,
# since the time until the next call is not its run time.
seen=' '
scan() {
  now=$(date +%s)
  place=-1 ahead=0 busy=0 what='' ages='' live=" $me " watched=' '
  while read -r state t pid _ started; do
    if [ "$state" = gone ]; then
      case "$seen" in *" $t "*) [ -n "${started:-}" ] && printf '%s\n' $((now - started)) >>"$took" ;; esac
      continue
    fi
    if [ "$t" = "${mine##*/}" ]; then
      place=1
      continue
    fi
    live="$live${pid:-} "
    if [ -n "${started:-}" ]; then
      watched="$watched$t "
      busy=$((busy + 1))
      what="$what, pid $pid for $(((now - started) / 60)) min"
      ages="$ages$((now - started))
"
    elif [ "$place" -lt 0 ]; then
      ahead=$((ahead + 1))
    fi
  done < <(perl -e "$sweep" "$tickets")
  # An older heavy.sh's entries: each holds a slot. The entry this script
  # writes for an older one to count is its own pid's.
  for e in ${legacy:+"$legacy"/[0-9]*}; do
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
    retakes=$((${retakes:-0} + 1))
    [ "$retakes" -le 20 ] || cannot "its ticket in $tickets keeps going missing"
    take
    continue
  fi
  # It runs when what runs and what waits ahead of it leave a slot free.
  if [ $((ahead + busy)) -lt "$slots" ]; then
    # The entry an older heavy.sh counts, written before a last count as it
    # does, so two arriving together cannot both miss the other.
    [ -z "$legacy" ] || printf '%s\n' "$me" >"$legacy/$me"
    # Marked running before that count too: two that took one number can
    # each miss the other's ticket at their first count, never both at this
    # one. Written in place, so the lock stays on the file.
    printf '%s %s %s\n' "$me" "$arrived" "$(date +%s)" >"$mine"
    scan
    if [ $((ahead + busy)) -lt "$slots" ]; then
      trap - INT TERM HUP
      # The command keeps this pid and fd 9, so its ticket is held exactly
      # while it runs.
      exec "$@"
    fi
    printf '%s %s\n' "$me" "$arrived" >"$mine"
    [ -z "$legacy" ] || rm -f "$legacy/$me"
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
