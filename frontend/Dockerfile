# Use the recommended Node.js tag for stability and security
FROM node:23-slim AS build

# Update and install security patches
RUN apt-get update && apt-get upgrade -y && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

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