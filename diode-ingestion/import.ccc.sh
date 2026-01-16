set -a
source .env
set +a

python3 dryrun_replay.py \
  -t grpcs://vcmy3535.cloud.netboxapp.com/diode \
  -a dryrun_replay \
  -v 1.0.0 \
  cisco_catalyst_center_worker_nbl-cisco-catalyst-center_416396884093086.json
