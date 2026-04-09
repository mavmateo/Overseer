path "secret/data/platform/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "database/creds/platform-app" {
  capabilities = ["read"]
}

path "pki/issue/site-mqtt-clients" {
  capabilities = ["create", "update"]
}

