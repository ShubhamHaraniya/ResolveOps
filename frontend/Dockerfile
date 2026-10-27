FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# next.config.ts reads BACKEND_URL when the routes manifest is built, so it is a build argument.
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
