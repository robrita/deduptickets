# Frontend Dockerfile
# Multi-stage build for development and production

# Stage 1: Base with dependencies
FROM node:20-slim as base

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Stage 2: Development
FROM base as development

# Copy source
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 3: Build for production
FROM base as builder

# Copy source
COPY . .

# Build the application
RUN npm run build

# Stage 4: Production with nginx
FROM nginx:alpine as production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
