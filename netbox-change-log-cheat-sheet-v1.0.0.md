# NetBox Change Log API Cheat Sheet (v1.0.0)

Last updated: 2026-01-28  
Instance: `https://pvkw7788.cloud.netboxapp.com`

> This cheat sheet focuses on the **global change log** endpoint:
>
> - `GET /api/core/object-changes/`
>
> Requirements:
> - A **NetBox API token** (not a Diode credential)
> - `jq` for human-readable formatting (`brew install jq` or `apt-get install jq`)

---

## Setup

Export these once per shell session (recommended):

```bash
export NETBOX_TOKEN="YOUR_REAL_API_TOKEN"
export BASE_URL="https://pvkw7788.cloud.netboxapp.com"
```

---

## 1) API root sanity check

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/"
```

---

## 2) Raw change log (latest 100)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?ordering=-time&limit=100"
```

---

## 3) Human-readable: who changed what (latest 100)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?ordering=-time&limit=100" | jq -r '.results[] |
  "\(.time) | \(.user.username) | \(.action.value) | \(.changed_object_type) | \(.object_repr)"'
```

---

## 4) Changes today (UTC)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?time__gte=$(date -u +%F)T00:00:00Z&ordering=-time&limit=1000"
```

---

## 5) Changes in the last 24 hours

### Linux (GNU date)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?time__gte=$(date -u -d '24 hours ago' +%FT%TZ)&ordering=-time"
```

### macOS (BSD date)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?time__gte=$(date -u -v-24H +%FT%TZ)&ordering=-time"
```

---

## 6) Changes by a specific user

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?user__username=admin&ordering=-time"
```

---

## 7) Changes by object type

### Devices

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?changed_object_type=dcim.device&ordering=-time"
```

### IP addresses

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?changed_object_type=ipam.ipaddress&ordering=-time"
```

---

## 8) Changes for a specific object ID

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?changed_object_id=1234"
```

---

## 9) Only creates / updates / deletes

```bash
# action = create | update | delete
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?action=update&ordering=-time"
```

---

## 10) Group changes by request_id (single user action)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?ordering=-time&limit=200" | jq -r '
  group_by(.request_id)[] |
  "REQUEST: \((.[0].request_id)) USER: \((.[0].user.username))\n" +
  (map("  - \(.time) \(.action.value) \(.changed_object_type) \(.object_repr)") | join("\n"))'
```

---

## 11) Field-level diffs (what actually changed)

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?ordering=-time&limit=50" | jq '
  .results[] |
  {
    time,
    user: .user.username,
    action: .action.value,
    object: .object_repr,
    changed_fields:
      (
        ((.prechange_data // {}) | keys) +
        ((.postchange_data // {}) | keys)
      )
      | unique
      | map(select((.prechange_data[.] // null) != (.postchange_data[.] // null)))
  }'
```

---

## 12) Export change log to CSV

```bash
curl -s   -H "Authorization: Token $NETBOX_TOKEN"   -H "Accept: application/json"   "$BASE_URL/api/core/object-changes/?ordering=-time&limit=1000" | jq -r '
  .results[] |
  [.time, .user.username, .action.value, .changed_object_type, .object_repr] |
  @csv'
```

---

## Notes

- Times are **UTC**
- Endpoint is **read-only**
- API tokens inherit user permissions
- `request_id` is extremely useful for grouping changes from a single UI action/script run
