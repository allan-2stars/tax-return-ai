# Production frontend — multi-stage build with standalone Next.js server

# ── Build stage ───────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /build

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source
COPY . .

# Build with standalone output
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ── Runtime stage ─────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

# Copy standalone server and public assets
COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/public ./public
COPY --from=builder /build/.next/static ./.next/static

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
