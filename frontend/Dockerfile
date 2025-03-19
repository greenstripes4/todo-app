# Use a Node.js base image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the Vue.js app files to the working directory
COPY . .

# Build the Vue.js app for production
ARG VITE_API_ENDPOINT
ENV VITE_API_ENDPOINT=$VITE_API_ENDPOINT
RUN npm run build

# Install serve to serve the built app
RUN npm install -g serve

# Expose the port that the app will listen on
EXPOSE 8888

# Start the app using serve
CMD ["serve", "-s", "dist", "-l", "8888"]
