#!/bin/sh
# Backup lógico (pg_dump -Fc) do Postgres de homologação -> bucket privado.
# Rede privada apenas. Retenção: últimos $KEEP dumps. Nunca imprime segredos.
set -eu
: "${DATABASE_URL:?}" "${BUCKET:?}" "${ENDPOINT:?}" "${AWS_ACCESS_KEY_ID:?}" "${AWS_SECRET_ACCESS_KEY:?}"
KEEP="${KEEP:-7}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
KEY="pg/homologacao-$TS.dump"
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" > /tmp/d.dump
pg_restore --list /tmp/d.dump > /dev/null
SIZE=$(wc -c < /tmp/d.dump)
aws --endpoint-url "$ENDPOINT" s3 cp /tmp/d.dump "s3://$BUCKET/$KEY" --only-show-errors
echo "backup ok key=$KEY bytes=$SIZE sha256=$(sha256sum /tmp/d.dump | cut -d' ' -f1)"
aws --endpoint-url "$ENDPOINT" s3 ls "s3://$BUCKET/pg/" | awk '{print $4}' | grep '\.dump$' | sort -r | tail -n +$((KEEP+1)) | while read -r k; do
  aws --endpoint-url "$ENDPOINT" s3 rm "s3://$BUCKET/pg/$k" --only-show-errors && echo "retention removed $k"
done
