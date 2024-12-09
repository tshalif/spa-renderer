# NGINX Proxy

This directory contains a POC implementation of a Nginx reverse proxy, which will:
1. Try to fetch from an S3 cache backend
2. Call spa-renderer backend if S3 cache returns 404, 403 response
