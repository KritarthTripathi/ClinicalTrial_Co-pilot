#!/bin/sh
# FAILS (exit 1) if a container on the internal network can reach the internet.
# Run in CI and on every deploy; keep the output as audit evidence.
NET=clinical-co-pilot_internal
IMG=$(docker compose images -q app 2>/dev/null | head -1)
[ -z "$IMG" ] && IMG=clinical-co-pilot-app
docker run --rm --network "$NET" "$IMG" python - <<'PY'
import socket, sys
leaks = []
for host, port in [("1.1.1.1", 443), ("8.8.8.8", 53), ("example.com", 443)]:
    try:
        socket.create_connection((host, port), timeout=3).close()
        leaks.append(f"{host}:{port}")
    except OSError:
        pass
if leaks:
    print("EGRESS DETECTED:", leaks); sys.exit(1)
print("OK: no outbound connectivity from internal network")
PY
