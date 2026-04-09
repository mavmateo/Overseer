import http from "node:http";
import { URL } from "node:url";
import mqtt from "mqtt";

const brokerUrl = process.env.MQTT_BROKER_URL || "mqtt://mosquitto:1883";
const port = Number(process.env.LIVE_FEED_PORT || 8090);
const topicFilter = process.env.LIVE_FEED_TOPIC_FILTER || "site/+/area/+/asset/+/#";

const subscribers = new Set();
const mqttClient = mqtt.connect(brokerUrl);

mqttClient.on("connect", () => {
  console.log(`connected to ${brokerUrl}`);
  mqttClient.subscribe(topicFilter, { qos: 1 });
});

mqttClient.on("message", (topic, payload) => {
  let parsedPayload;
  try {
    parsedPayload = JSON.parse(payload.toString("utf-8"));
  } catch {
    parsedPayload = payload.toString("utf-8");
  }
  const event = JSON.stringify({
    topic,
    receivedAt: new Date().toISOString(),
    payload: parsedPayload
  });
  for (const response of subscribers) {
    response.write(`data: ${event}\n\n`);
  }
});

const server = http.createServer((request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  if (url.pathname === "/healthz") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "ok", connected: mqttClient.connected }));
    return;
  }
  if (url.pathname !== "/stream") {
    response.writeHead(404, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: "not found" }));
    return;
  }
  response.writeHead(200, {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
    connection: "keep-alive"
  });
  response.write("\n");
  subscribers.add(response);
  request.on("close", () => {
    subscribers.delete(response);
  });
});

server.listen(port, () => {
  console.log(`live feed adapter listening on ${port}`);
});
