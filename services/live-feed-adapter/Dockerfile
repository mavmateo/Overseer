FROM node:20-slim

WORKDIR /app

COPY services/live-feed-adapter/package.json /app/package.json
RUN npm install

COPY services/live-feed-adapter/src /app/src

EXPOSE 8090

CMD ["npm", "start"]

