FROM node:20-slim AS builder

WORKDIR /app

ARG VITE_API_BASE=https://octane-api.fly.dev

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN VITE_API_BASE=$VITE_API_BASE npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
