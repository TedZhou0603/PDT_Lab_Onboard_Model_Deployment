#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

sudo apt-get update

sudo apt-get install -y \
    ros-humble-camera-calibration \
    ros-humble-image-proc \
    ros-humble-apriltag-ros \
    ros-humble-camera-info-manager \
    ros-humble-image-transport

echo "Checking installed packages..."

for pkg in camera_calibration image_proc apriltag_ros; do
    ros2 pkg prefix "$pkg"
done

echo "Camera tools installed successfully."
