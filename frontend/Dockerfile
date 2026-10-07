FROM node:22-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --include=dev --legacy-peer-deps --omit=optional --ignore-scripts --no-audit --no-fund
RUN npm install --no-save --ignore-scripts --no-audit --no-fund @rolldown/binding-linux-arm64-gnu@1.2.9

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
