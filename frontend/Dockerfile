# Use a specific Node.js v22 Alpine tag with fewer known vulnerabilities
FROM node:22.15.0-alpine AS build

# Update and install security patches (using apk for alpine)
RUN apk update && apk upgrade --no-cache && apk add --no-cache bash

# Set NODE_ENV to production for optimized builds
ENV NODE_ENV=production

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application to the working directory
COPY . .

# Add this line to enable legacy OpenSSL provider as a workaround (needed for Node >= 17)
ENV NODE_OPTIONS=--openssl-legacy-provider

# Build the application for production
RUN npm run build

# Use Nginx to serve the production build
FROM nginx:alpine

# Copy the production build from the build stage
COPY --from=build /app/build /usr/share/nginx/html

# Expose the port the app runs on
EXPOSE 80

# Start the web server
CMD ["nginx", "-g", "daemon off;"]