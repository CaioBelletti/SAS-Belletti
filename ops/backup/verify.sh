#!/bin/sh
# Verifica restauração do dump mais recente em Postgres temporário DENTRO do container (isolado, descartável).
set -eu
: "${DATABASE_URL:?}" "${BUCKET:?}" "${ENDPOINT:?}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
K=$(aws --endpoint-url "$ENDPOINT" s3 ls "s3://$BUCKET/pg/" | awk '{print $4}' | grep '\.dump$' | sort | tail -1)
echo "verificando $K"
aws --endpoint-url "$ENDPOINT" s3 cp "s3://$BUCKET/pg/$K" /tmp/v.dump --only-show-errors
echo "sha256=$(sha256sum /tmp/v.dump | cut -d' ' -f1)"
export PGDATA=/tmp/pgv; mkdir -p $PGDATA; chown postgres $PGDATA; chmod 700 $PGDATA
su postgres -c "initdb -D $PGDATA -U verify --auth=trust >/dev/null && pg_ctl -D $PGDATA -o '-c listen_addresses= -c unix_socket_directories=/tmp' -w start >/dev/null"
R="psql -h /tmp -U verify -At"
$R -d postgres -c "create database restoretest" >/dev/null
pg_restore -h /tmp -U verify -d restoretest --no-owner --exit-on-error /tmp/v.dump
Q="select count(*) from information_schema.tables where table_schema='public'"
echo "restaurado: tabelas=$($R -d restoretest -c "$Q") origem=$(psql "$DATABASE_URL" -At -c "$Q")"
for t in auth_user cozinha_prato cozinha_mesa cozinha_pedidocozinha; do
  echo "$t restaurado=$($R -d restoretest -c "select count(*) from $t" 2>&1|tail -1) origem=$(psql "$DATABASE_URL" -At -c "select count(*) from $t" 2>&1|tail -1)"
done
su postgres -c "pg_ctl -D $PGDATA -m immediate stop >/dev/null"; rm -rf $PGDATA /tmp/v.dump
echo "VERIFY OK"
