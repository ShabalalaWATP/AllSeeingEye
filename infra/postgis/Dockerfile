# The production database: the pinned upstream PostGIS image with two hardening steps.
# CI's PostgreSQL service runs the same pinned base (scripts/tests/test_database_image_pin.py),
# so PostgreSQL and PostGIS behaviour is identical; only system packages and the
# privilege-drop helper differ.
FROM postgis/postgis:16-3.6-alpine@sha256:d5955943c6e633219d80bd1d7fd986a097fdd44f3979c53d4839d62647bba478

# Apply Alpine security updates to packages inherited from the pinned base. PostgreSQL
# and PostGIS are built from source under /usr/local, so apk does not change them.
# The entrypoint's single `gosu postgres` call is served by Alpine's su-exec (a small C
# helper with the same user-then-command interface), replacing the Go-built gosu
# binary whose bundled runtime the upstream image does not rebuild. Deleting the old
# binary (rather than overwriting it) lets image scanners see that it is gone.
RUN apk upgrade --no-cache \
    && apk add --no-cache su-exec \
    && rm /usr/local/bin/gosu \
    && mkdir -p /usr/local/sbin \
    && ln -s /sbin/su-exec /usr/local/sbin/gosu \
    && gosu nobody true
