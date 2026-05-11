#!/bin/sh
set -eu

mkdir -p /app/.next /app/node_modules /tmp/.npm
chown -R node:node /app/.next /app/node_modules /tmp/.npm

exec su-exec node "$@"
