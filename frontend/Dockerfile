FROM node:22-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 5173

# Run dev server with host flag for Docker networking
CMD ["npm", "run", "dev", "--", "--host"]
