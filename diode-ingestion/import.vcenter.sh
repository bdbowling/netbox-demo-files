set -a
source .env
set +a

python3 dryrun_replay.py \
  -t grpcs://vcmy3535.cloud.netboxapp.com/diode \
  -a dryrun_replay \
  -v 1.0.0 \
  cc-worker_nbl-vmware-vcenter_416241942330057.json
