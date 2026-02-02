#!/usr/bin/env bash
# Samples QGIS resident memory (RSS in MB) every 60 seconds.
# Usage: ./scripts/memory_monitor.sh [output_file]
# Stop with Ctrl-C.

OUTFILE="${1:-qgis_memory.log}"

echo "timestamp_utc	rss_mb" > "$OUTFILE"
echo "Logging QGIS memory to $OUTFILE (Ctrl-C to stop)"

while true; do
    # Sum RSS of all qgis processes (includes NixOS .qgis-wrapped)
    rss_kb=$(ps aux 2>/dev/null | awk '/[q]gis|[.]qgis-wrapped/ {s+=$6} END {print s+0}')
    if [ "$rss_kb" -gt 0 ] 2>/dev/null; then
        rss_mb=$(awk "BEGIN {printf \"%.1f\", $rss_kb / 1024}")
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)	${rss_mb}" | tee -a "$OUTFILE"
    else
        echo "$(date -u +%H:%M:%S) — no qgis process found, waiting…"
    fi
    sleep 60
done
