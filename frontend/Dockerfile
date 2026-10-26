FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# nginx-unprivileged работает не от root и слушает порт 8080.
# Актуальная стабильная ветка nginx (1.30) на свежем Alpine.
FROM nginxinc/nginx-unprivileged:1.30-alpine

# Подтягиваем исправления пакетов ОС, выпущенные после сборки базового образа
USER root
RUN apk upgrade --no-cache
USER 101

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
