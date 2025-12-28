FROM node:20-slim

WORKDIR /app

# Install dependencies first for caching
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Run dev server with host flag to allow external access
CMD ["npm", "run", "dev", "--", "--host"]
