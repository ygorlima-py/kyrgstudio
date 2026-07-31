# syntax=docker/dockerfile:1

FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

ARG VITE_AUTH_CSRF_COOKIE_NAME=kyrg_csrf_token
ENV VITE_AUTH_CSRF_COOKIE_NAME=${VITE_AUTH_CSRF_COOKIE_NAME}

RUN npm run build

FROM nginx:1.31-alpine AS runtime

ENV API_UPSTREAM=api:8000
ENV NGINX_MAX_REQUEST_BODY_SIZE=2100m

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]