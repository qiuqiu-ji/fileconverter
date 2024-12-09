FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm install -g next
RUN npm run build

ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000
CMD ["npm", "start"]