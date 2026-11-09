FROM node:22-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202 AS build
WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm ci
COPY src ./src
RUN npm run build
FROM build AS test
COPY test ./test
RUN npm run build
USER node
CMD ["node", "--test", "dist/test/client.test.js", "dist/test/process.test.js"]
FROM node:22-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202
WORKDIR /app
COPY --from=build /app/dist/src ./dist/src
COPY package.json ./
USER node
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 CMD ["node", "dist/src/healthcheck.js"]
CMD ["node", "dist/src/main.js"]
