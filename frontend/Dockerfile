FROM node:18-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Create non-root user and set permissions
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5173/ || exit 1

CMD ["npm", "run", "dev", "--", "--host"]
