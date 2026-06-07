#!/bin/bash
cd /etc/nginx/ssl

if [ ! -f "botsda.hackquest.com/fullchain.pem" ]; then
    mkdir -p botsda.hackquest.com
    
    docker run --rm -v "$(pwd)":/data -v "$(pwd)/.well-known":/.well-known certbot/certbot certonly \
        --webroot -w /.well-known \
        --email "izi.vislobokov@mail.ru" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d botsda.hackquest.com
    
    cp .well-known/* botsda.hackquest.com/ 2>/dev/null || true
fi
