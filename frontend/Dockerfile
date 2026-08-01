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

ARG VITE_MAX_UPLOAD_BYTES=2147483648
ENV VITE_MAX_UPLOAD_BYTES=${VITE_MAX_UPLOAD_BYTES}

ARG VITE_ACCEPTED_MEDIA_TYPES=video/mp4,video/quicktime,video/webm,video/x-msvideo,audio/mpeg,audio/mp4,audio/ogg,audio/wav,audio/x-wav,audio/webm
ENV VITE_ACCEPTED_MEDIA_TYPES=${VITE_ACCEPTED_MEDIA_TYPES}

RUN npm run build

FROM nginx:1.31-alpine AS runtime

ENV API_UPSTREAM=api:8000
ENV NGINX_MAX_REQUEST_BODY_SIZE=2100m

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]