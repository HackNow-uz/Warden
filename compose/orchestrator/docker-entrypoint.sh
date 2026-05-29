#!/bin/sh
# Cron Linux'da konteyner env'ini meros olmaydi. Shu sababli joriy env'ni
# /etc/environment'ga yozamiz (cron PAM orqali o'qiydi), keyin cron'ni boshlaymiz.
printenv | grep -vE '^(HOME|PWD|TERM|SHLVL|_|no_proxy)=' >> /etc/environment
exec cron -f
