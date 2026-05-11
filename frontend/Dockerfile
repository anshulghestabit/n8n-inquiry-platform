# Next.js development image for the browser dashboard.
FROM node:20-alpine

WORKDIR /app
ENV NPM_CONFIG_CACHE=/tmp/.npm
RUN apk add --no-cache su-exec

# Install dependencies before source copy so unchanged package files reuse cache.
COPY --chmod=0444 package*.json ./
RUN npm install

# Copy only files needed by the Next.js dev server. Avoid recursive context
# copies so local secrets or generated files cannot be baked into the image.
COPY --chmod=0444 next.config.js tsconfig.json next-env.d.ts ./
COPY --chmod=0555 src ./src
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/frontend-entrypoint
RUN mkdir -p .next /tmp/.npm && chown -R node:node .next /tmp/.npm

# Repair writable dev-server volumes, then run as the non-root node user.
ENTRYPOINT ["frontend-entrypoint"]
CMD ["npm", "run", "dev"]
