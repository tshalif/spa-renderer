#!/bin/sh

if grep ENV_SUBST_ /etc/nginx/conf.d/default.conf > /dev/null; then
    echo 1>&2 error: unsubstituted '@@' variable found in /etc/nginx/conf.d/default.conf
    exit 1
fi

