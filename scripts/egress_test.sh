#!/bin/sh
# Fails (exit 1) if a container on the chosen network can reach the internet.
# Normal use:        sh scripts/egress_test.sh
# Positive control:  NET=bridge sh scripts/egress_test.sh      (must report EGRESS DETECTED)
NET=${NET:-clinical-co-pilot_internal}
IMG=${IMG:-clinical-co-pilot-app}
docker run --rm --network "$NET" --entrypoint python "$IMG" -c "
import socket, sys
leaks = []
for host, port in [('1.1.1.1', 443), ('8.8.8.8', 53), ('example.com', 443)]:
    try:
        socket.create_connection((host, port), timeout=3).close()
        leaks.append(host)
    except OSError:
        pass
print('EGRESS DETECTED: ' + str(leaks) if leaks else 'OK: no outbound connectivity from this network')
sys.exit(1 if leaks else 0)
"
