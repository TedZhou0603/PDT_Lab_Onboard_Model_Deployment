import socket
import struct
import threading

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

HOST = "127.0.0.1"
IMAGE_PORT = 5001
ANSWER_PORT = 5000


class AlpamayoBridge(Node):
    def __init__(self):
        super().__init__("alpamayo_bridge")
        self.answer_pub = self.create_publisher(String, "/alpamayo/answer", 10)
        self.declare_parameter("image_topic", "/image_raw")
        image_topic = self.get_parameter("image_topic").value
        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, qos_profile_sensor_data
        )
        self.get_logger().info(f"Subscribing to camera topic: {image_topic}")
        self.image_client = None
        self.client_lock = threading.Lock()
        threading.Thread(target=self.image_server, daemon=True).start()
        threading.Thread(target=self.answer_server, daemon=True).start()
        self.get_logger().info("Alpamayo bridge started")

    def image_callback(self, msg):
        self.get_logger().info(
            f"Received image: {msg.width}x{msg.height}, encoding={msg.encoding}"
        )
        try:
            raw = np.frombuffer(msg.data, dtype=np.uint8)
            if msg.height <= 0 or msg.width <= 0 or msg.step <= 0:
                return
            if raw.size < msg.height * msg.step:
                self.get_logger().warn("Incomplete camera image")
                return

            rows = raw[:msg.height * msg.step].reshape(msg.height, msg.step)
            if msg.encoding == "bayer_rggb8":
                if msg.step < msg.width:
                    return
                bayer = rows[:, :msg.width]
                image = cv2.cvtColor(bayer, cv2.COLOR_BayerRG2BGR)
            elif msg.encoding in ("rgb8", "bgr8"):
                row_bytes = msg.width * 3
                if msg.step < row_bytes:
                    return
                image = rows[:, :row_bytes].reshape(msg.height, msg.width, 3)
                if msg.encoding == "rgb8":
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                self.get_logger().warn(f"Unsupported image encoding: {msg.encoding}")
                return

            success, encoded = cv2.imencode(
                ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            if not success:
                self.get_logger().warn("JPEG encoding failed")
                return
            payload = encoded.tobytes()
            packet = struct.pack("!I", len(payload)) + payload
            with self.client_lock:
                client = self.image_client
                if client is not None:
                    try:
                        client.sendall(packet)
                        self.get_logger().info(
                            f"Sent JPEG frame: {len(payload)} bytes"
                        )
                    except OSError:
                        try:
                            client.close()
                        except OSError:
                            pass
                        self.image_client = None
                else:
                    self.get_logger().warn("No Alpamayo image TCP client connected")
        except Exception as e:
            self.get_logger().error(f"Image error: {e}")

    def image_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, IMAGE_PORT))
            server.listen(1)
            print("Image bridge listening on port 5001", flush=True)
            while rclpy.ok():
                client, _ = server.accept()
                with self.client_lock:
                    if self.image_client is not None:
                        self.image_client.close()
                    self.image_client = client
                print("Alpamayo image client connected", flush=True)

    def answer_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, ANSWER_PORT))
            server.listen(1)
            print("Answer bridge listening on port 5000", flush=True)
            while rclpy.ok():
                client, _ = server.accept()
                print("Alpamayo answer client connected", flush=True)
                with client:
                    buffer = b""
                    while rclpy.ok():
                        data = client.recv(4096)
                        if not data:
                            break
                        buffer += data
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            answer = line.decode("utf-8", errors="replace").strip()
                            if answer:
                                msg = String()
                                msg.data = answer
                                self.answer_pub.publish(msg)
                                print(f"Published answer: {answer}", flush=True)


def main():
    rclpy.init()
    node = AlpamayoBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()