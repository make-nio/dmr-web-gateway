FROM node:22-alpine AS build
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
FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/dist/src ./dist/src
COPY package.json ./
USER node
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD ["node", "dist/src/healthcheck.js"]
CMD ["node", "dist/src/main.js"]
