import socket
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node("alpamayo_bridge")
publisher = node.create_publisher(String, "/alpamayo/answer", 10)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", 5000))
server.listen(1)

print("Waiting for Alpamayo...", flush=True)

try:
    while True:
        conn, _ = server.accept()
        with conn:
            with conn.makefile("r", encoding="utf-8") as stream:
                for line in stream:
                    msg = String()
                    msg.data = line.rstrip("\n")
                    publisher.publish(msg)
                    print("Published:", msg.data, flush=True)

except KeyboardInterrupt:
    print("\nStopping ROS 2 bridge...")
finally:
    server.close()
    node.destroy_node()
    rclpy.shutdown()
