#!/bin/bash
# Deploy ODRMitra to the DigitalOcean droplet (shared with pcs-pyq).
#
# The pcs_pyq stack must be STOPPED first to free RAM (2GB droplet):
#   ssh root@147.182.186.207 "cd /opt/pcs-pyq && docker compose --profile frontend stop"
# and is restored after the competition with:
#   ssh root@147.182.186.207 "cd /opt/pcs-pyq && docker compose --profile frontend up -d"
#
# Ships the committed tree (git archive → respects .gitignore, so no secrets
# in the bundle); .secrets.toml is copied separately and never enters git or
# the Docker image (dockerignored, runtime-mounted).
set -e

HOST=root@147.182.186.207
KEY=~/.ssh/id_ed25519
DEST=/opt/odrmitra

echo "==> bundling committed tree"
git archive --format=tar.gz -o /tmp/odrmitra.tar.gz HEAD

echo "==> uploading"
ssh -i "$KEY" "$HOST" "mkdir -p $DEST"
scp -i "$KEY" /tmp/odrmitra.tar.gz "$HOST:/tmp/"
scp -i "$KEY" backend/config/.secrets.toml "$HOST:/tmp/odrmitra.secrets.toml"

echo "==> extracting + building + starting"
ssh -i "$KEY" "$HOST" "
  set -e
  cd $DEST
  tar xzf /tmp/odrmitra.tar.gz
  mkdir -p backend/config
  mv /tmp/odrmitra.secrets.toml backend/config/.secrets.toml
  docker compose -f docker-compose.prod.yml up -d --build
"

echo "==> done — stack status:"
ssh -i "$KEY" "$HOST" "cd $DEST && docker compose -f docker-compose.prod.yml ps"
