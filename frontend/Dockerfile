# Next.js development image for the browser dashboard.
FROM node:20-alpine

WORKDIR /app
ENV NPM_CONFIG_CACHE=/tmp/.npm

# Install dependencies before source copy so unchanged package files reuse cache.
COPY package*.json ./
RUN npm install

# Copy only files needed by the Next.js dev server. Avoid recursive context
# copies so local secrets or generated files cannot be baked into the image.
COPY --chown=node:node next.config.js tsconfig.json next-env.d.ts ./
COPY --chown=node:node src ./src
RUN mkdir -p .next && chown node:node .next

# Run the dev server as the non-root user provided by the base image.
USER node

# Start the Next.js dev server exposed by docker-compose.
CMD ["npm", "run", "dev"]
