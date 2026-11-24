
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

        self.answer_pub = self.create_publisher(
            String, "/alpamayo/answer", 10
        )

        self.image_sub = self.create_subscription(
            Image,
            "/image_raw",
            self.image_callback,
            qos_profile_sensor_data,
        )

        self.image_client = None
        self.client_lock = threading.Lock()

        threading.Thread(
            target=self.image_server,
            daemon=True,
        ).start()

        threading.Thread(
            target=self.answer_server,
            daemon=True,
        ).start()

        self.get_logger().info("Alpamayo bridge started")

    def image_callback(self, msg):
        if msg.encoding not in ("rgb8", "bgr8"):
            self.get_logger().warn(
                f"Unsupported image encoding: {msg.encoding}"
            )
            return

        try:
            channels = 3
            row_bytes = msg.width * channels

            if msg.step < row_bytes:
                return

            raw = np.frombuffer(msg.data, dtype=np.uint8)

            if raw.size < msg.height * msg.step:
                return

            image = raw[:msg.height * msg.step].reshape(
                msg.height, msg.step
            )[:, :row_bytes].reshape(
                msg.height, msg.width, channels
            )

            if msg.encoding == "rgb8":
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            success, encoded = cv2.imencode(
                ".jpg",
                image,
                [cv2.IMWRITE_JPEG_QUALITY, 80],
            )

            if not success:
                return

            payload = encoded.tobytes()
            packet = struct.pack("!I", len(payload)) + payload

            with self.client_lock:
                client = self.image_client

                if client is not None:
                    try:
                        client.sendall(packet)
                    except OSError:
                        try:
                            client.close()
                        except OSError:
                            pass
                        self.image_client = None

        except Exception as e:
            self.get_logger().error(f"Image error: {e}")

    def image_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
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
            server.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
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

                            answer = line.decode(
                                "utf-8", errors="replace"
                            ).strip()

                            if answer:
                                msg = String()
                                msg.data = answer
                                self.answer_pub.publish(msg)

                                print(
                                    f"Published answer: {answer}",
                                    flush=True,
                                )


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
