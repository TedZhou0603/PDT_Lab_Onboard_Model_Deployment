#!/usr/bin/env python3
"""Bidirectional ROS 2 topic relay between isolated DDS domains over TCP.
Run once per side with --side local or --side network.
"""
import argparse
import socket
import struct
import threading
import time
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import serialize_message, deserialize_message

MAX_FRAME = 100 * 1024 * 1024

def recvall(sock, n):
    buf = bytearray()
    while len(buf) < n:
        data = sock.recv(n - len(buf))
        if not data:
            raise ConnectionError('Socket closed')
        buf.extend(data)
    return bytes(buf)

class Bridge(Node):
    def __init__(self, cfg, side, host, port):
        super().__init__('tcp_dds_bridge_' + side)
        self.side = side
        self.host, self.port = host, port
        self.sock = None
        self.lock = threading.Lock()
        self.pubs = {}
        self.subs = []
        self.qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=5,
                              reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.VOLATILE)
        # local side reads ECU topics and publishes Jetson topics.
        # network side publishes ECU topics and reads Jetson topics.
        for route in cfg['routes']:
            source_side = route['source']
            name = route['topic']
            cls = get_message(route['type'])
            if source_side == side:
                self.subs.append(self.create_subscription(
                    cls, name, lambda msg, topic=name: self.send(topic, serialize_message(msg)), self.qos))
                self.get_logger().info('Subscribe: ' + name)
            else:
                self.pubs[name] = (self.create_publisher(cls, name, self.qos), cls)
                self.get_logger().info('Publish: ' + name)
        threading.Thread(target=self.connection_loop, daemon=True).start()

    def send(self, topic, payload):
        topic_bytes = topic.encode('utf-8')
        frame = struct.pack('!H', len(topic_bytes)) + topic_bytes + payload
        if len(frame) > MAX_FRAME:
            return
        with self.lock:
            if self.sock is None:
                return
            try:
                self.sock.sendall(struct.pack('!I', len(frame)) + frame)
            except OSError:
                try: self.sock.close()
                except OSError: pass
                self.sock = None

    def connection_loop(self):
        while rclpy.ok():
            try:
                if self.side == 'local':
                    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind((self.host, self.port))
                    listener.listen(1)
                    self.get_logger().info(f'Waiting for network bridge on {self.host}:{self.port}')
                    conn, _ = listener.accept()
                    listener.close()
                else:
                    conn = socket.create_connection((self.host, self.port), timeout=5)
                conn.settimeout(None)
                with self.lock:
                    self.sock = conn
                self.get_logger().info('TCP bridge connected')
                while rclpy.ok():
                    size = struct.unpack('!I', recvall(conn, 4))[0]
                    if size > MAX_FRAME or size < 3:
                        raise ValueError('Invalid frame size')
                    data = recvall(conn, size)
                    tlen = struct.unpack('!H', data[:2])[0]
                    topic = data[2:2+tlen].decode('utf-8')
                    if topic in self.pubs:
                        pub, cls = self.pubs[topic]
                        pub.publish(deserialize_message(data[2+tlen:], cls))
            except (OSError, ConnectionError, ValueError) as exc:
                self.get_logger().warning(f'Bridge disconnected: {exc}')
            finally:
                with self.lock:
                    if self.sock is not None:
                        try: self.sock.close()
                        except OSError: pass
                    self.sock = None
            time.sleep(2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--side', required=True, choices=['local', 'network'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=48765)
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    rclpy.init()
    node = Bridge(cfg, args.side, args.host, args.port)
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__': main()
