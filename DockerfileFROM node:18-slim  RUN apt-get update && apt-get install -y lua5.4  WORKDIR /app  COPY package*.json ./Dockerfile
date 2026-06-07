FROM node:18-slim

RUN apt-get update && apt-get install -y lua5.4

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "start"]
