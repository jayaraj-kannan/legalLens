# Stage 1: Build Vue 3 Frontend
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx configurations
RUN rm -rf /etc/nginx/conf.d/*

# Copy built frontend assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy dynamic nginx template (automatically processed by official nginx docker entrypoint)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Default backend connection variables (overridable in docker-compose / k8s)
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8080

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
