const mqtt = require("mqtt");

const brokerUrl = "mqtt://192.168.1.231:1883";
const topic = "sarayu/d1/topic29";

let totalValuesReceived = 0;
let valuesThisSecond = 0;
let lastValues = [];

const client = mqtt.connect(brokerUrl);

client.on("connect", () => {
  console.log(`Connected to MQTT broker at ${brokerUrl}`);
  client.subscribe(topic, (err) => {
    if (!err) {
      console.log(`Subscribed to topic: ${topic}`);
    } else {
      console.error("Subscription error:", err);
    }
  });
});

client.on("message", (receivedTopic, message) => {
  if (receivedTopic === topic) {
    const valueCount = message.length / 2; // 2 bytes per uint16 value
    totalValuesReceived += valueCount;
    valuesThisSecond += valueCount;

    // Parse and save a preview of the values
    const values = [];
    for (let i = 0; i < valueCount; i++) {
      values.push(message.readUInt16LE(i * 2));
    }
    lastValues = values;
  }
});

setInterval(() => {
  console.clear();
  // console.log(`Total values received: ${totalValuesReceived}`);
  // console.log(`Values received in last second: ${valuesThisSecond}`);

  if (lastValues.length > 0) {
    // const slice1 = lastValues.slice(20580, 21580);
    // const slice2 = lastValues.slice(41060, 45256);
    // console.log(`Values slice 1: ${slice1.join(', ')}`);
    // console.log(`Values slice 2: ${slice2.join(', ')}`);

    console.log(`First 10 values: ${lastValues.slice(0, 35).join(", ")}`);
  }

  valuesThisSecond = 0;
}, 1000);
