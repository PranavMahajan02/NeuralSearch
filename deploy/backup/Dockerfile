# Backup/restore tools: pg_dump/pg_restore from the SAME major version as the
# server (postgres:16) plus Python for scripts/backup.py and scripts/restore.py.
FROM postgres:16

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-cryptography \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /backups
CMD ["python3", "/scripts/backup.py"]
