# syntax=docker/dockerfile:1

# The frontend image (spec 10, ADR 0009). Iteration 5 has the dev target: Vite's dev server,
# with the source mounted by compose. Iteration 7 adds a build stage and an nginx prod target.

# The same Node as frontend/.nvmrc (ADR 0016).
FROM node:24.22.3-alpine AS base

WORKDIR /app

# Dependencies only: this layer rebuilds only when the lockfile changes. .npmrc comes along
# because it makes npm ci refuse a Node outside package.json's engines.
FROM base AS deps

COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm npm ci

# Local development: compose mounts the source over /app and keeps this image's node_modules.
FROM deps AS dev

COPY . .

EXPOSE 5173
# --host: listen on every interface, so the port compose publishes reaches Vite.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
