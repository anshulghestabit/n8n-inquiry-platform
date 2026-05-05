# Next.js development image for the browser dashboard.
FROM node:20-alpine

WORKDIR /app

# Install dependencies before source copy so unchanged package files reuse cache.
COPY package*.json ./
RUN npm install

COPY . .

# Start the Next.js dev server exposed by docker-compose.
CMD ["npm", "run", "dev"]
