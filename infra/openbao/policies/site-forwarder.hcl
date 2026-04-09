path "secret/data/sites/{{identity.entity.aliases.auth_jwt_*.metadata.site_id}}/*" {
  capabilities = ["read"]
}

path "pki/issue/site-forwarder" {
  capabilities = ["create", "update"]
}

