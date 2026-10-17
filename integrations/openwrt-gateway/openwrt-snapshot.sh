#!/bin/sh
# Fixed read-only snapshot. Ignore SSH_ORIGINAL_COMMAND and all client input.
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
emit() {
 key="$1"; shift
 printf '"%s":' "$key"
 if value=$("$@" 2>/dev/null); then printf '%s' "$value"; else printf 'null'; fi
}
printf '{'
emit board ubus call system board
printf ','; emit info ubus call system info
printf ','; emit wan ubus call network.interface.wan status
printf ','; emit lab ubus call network.interface.lan status
wan_device=$(ubus call network.interface.wan status 2>/dev/null | jsonfilter -e '@.l3_device')
case "$wan_device" in ''|*[!a-zA-Z0-9_.:-]*) wan_device=;; esac
printf ','; emit wan_device ubus call network.device status "{\"name\":\"$wan_device\"}"
printf ','; emit leases ubus call luci-rpc getDHCPLeases '{"family":4}'
printf ','; emit hints ubus call luci-rpc getHostHints
printf ',"radios":['
separator=''
for object in $(ubus list 'hostapd.*' 2>/dev/null); do
 device=${object#hostapd.}
 case "$device" in ''|*[!a-zA-Z0-9_.:-]*) continue;; esac
 printf '%s{' "$separator"; emit status ubus call "$object" get_status
 printf ','; emit stations ubus call iwinfo assoclist "{\"device\":\"$device\"}"
 printf '}'; separator=','
done
printf '],"extras":'
. /usr/share/libubox/jshn.sh
json_init
if neighbors=$(ip -4 neigh show 2>/dev/null); then json_add_string neighbors "$neighbors"; else json_add_null neighbors; fi
json_add_string cpu "$(head -n 1 /proc/stat)"
json_add_string ping "$(ping -c 1 -W 2 1.1.1.1 2>/dev/null)"
json_dump
printf '}\n'
