FROM nginx:latest

ENV PORT 8080

ENV NGINX_ENVSUBST_FILTER="^ENV_SUBST_" \
 ENV_SUBST_LISTEN_PORT=${PORT} \
 ENV_SUBST_S3_CACHE_HOST=cw-prerender-cache.sfo3.digitaloceanspaces.com \
 ENV_SUBST_SPA_RENDER_HOST=spa-renderer-356378388264.northamerica-northeast1.run.app \
 ENV_SUBST_UA_NEXUS5X="Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.89 Mobile Safari/537.36" \
 ENV_SUBST_UA_DEFAULT="Mozilla/5.0 (Linux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.89 Safari/537.36" \
 ENV_SUBST_INTERNAL_PATH_TOKEN=ahvah6aH

RUN mkdir -p /etc/nginx/templates

COPY nginx.conf.in /etc/nginx/templates/default.conf.template

COPY proxy_params /etc/nginx

COPY 25-verify-envsubst.sh /docker-entrypoint.d

EXPOSE ${PORT}

