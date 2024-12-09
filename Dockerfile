FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

ENV PORT=3000
ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_URL=https://fileconverter-vg92.onrender.com

EXPOSE 3000
CMD ["npm", "start"]