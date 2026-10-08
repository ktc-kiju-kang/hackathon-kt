# web 이미지 — dev(make dev, src 마운트) / prod(make serve, 빌드 후 next start)
FROM node:20-slim AS deps
WORKDIR /app/frontend
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM deps AS src
ENV NEXT_TELEMETRY_DISABLED=1
COPY . .

FROM src AS dev
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]

FROM src AS prod
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build
EXPOSE 3000
CMD ["./node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
