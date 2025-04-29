# Use an official Node.js runtime as a parent image
FROM node:20-bullseye-slim AS build

# Update and install security patches
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Update and install security patches
RUN apt-get update && apt-get upgrade -y && apt-get clean

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

# Use a lightweight web server to serve the production build
FROM nginx:alpine

# Copy the production build from the previous stage
COPY --from=build /app/build /usr/share/nginx/html

# Expose the port the app runs on
EXPOSE 80

# Start the web server
CMD ["nginx", "-g", "daemon off;"]