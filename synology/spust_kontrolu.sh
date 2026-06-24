#!/bin/bash
# Spuštění GitHub Actions workflow pro je-uz-novy-letak
# Umístění na NAS: /volume1/docker/je-uz-novy-letak/spust_kontrolu.sh

PAT=$(cat /volume1/docker/je-uz-novy-letak/github_pat.txt)
LOG_FILE="/volume1/docker/je-uz-novy-letak/spusteni.log"
REPO="romanlowinger/je-uz-novy-letak"
WORKFLOW="check.yml"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
    -d '{"ref":"main"}')

if [ "$HTTP_CODE" = "204" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') OK – workflow spuštěn (HTTP 204)" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') CHYBA – GitHub odpověděl HTTP $HTTP_CODE" >> "$LOG_FILE"
fi
