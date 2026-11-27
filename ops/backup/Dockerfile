FROM postgres:18-alpine
RUN apk add --no-cache aws-cli
COPY backup.sh verify.sh /
RUN chmod +x /backup.sh /verify.sh
ENTRYPOINT []
CMD ["sh","-c","if [ \"${MODE:-backup}\" = verify ]; then exec /verify.sh; else exec /backup.sh; fi"]
