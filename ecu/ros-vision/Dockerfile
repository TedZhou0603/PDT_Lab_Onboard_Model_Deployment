FROM ros:jazzy-ros-base

RUN apt-get update && apt-get install -y \
    ros-jazzy-camera-calibration \
    ros-jazzy-image-proc \
    ros-jazzy-apriltag-ros \
    && rm -rf /var/lib/apt/lists/*

RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc

CMD ["bash"]
