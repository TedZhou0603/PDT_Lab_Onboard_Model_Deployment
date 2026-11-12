# Alpamayo 1.5 — Jetson AGX Orin

Running NVIDIA Alpamayo 1.5 (10B) on the Jetson AGX Orin 64GB with ROS 2 Humble.

The model takes camera images and a text prompt, generates a response, and sends the output to a ROS 2 topic through a TCP bridge.

## Start Alpamayo

On the Jetson host, run:

```bash
~/alpamayo.sh
```

This opens the Alpamayo Docker container with GPU access.

If the container is already running, open another terminal and enter it:

```bash
sudo docker exec -it alpamayo-dev bash
```

## Start ROS 2

```bash
sudo docker run --rm -it \
  --name ros2-dev \
  --network host \
  ros:humble-ros-base \
  bash
```

Inside the ROS 2 container:

```bash
source /opt/ros/humble/setup.bash
python3 /tmp/alpamayo_bridge.py
```

The bridge listens on port `5000` and publishes to `/alpamayo/answer`.

Note: The bridge script must be copied or mounted into the ROS 2 container before running it.

## Run the VLA

Inside the Alpamayo container:

```bash
cd /workspace/Alpamayo1.5/repo
python test_single_image.py
```

Enter questions about the camera images when prompted. Type `x` to exit.

The current script runs visual question answering (VQA) using two camera frames.

## View ROS 2 Output

Open another terminal:

```bash
sudo docker exec -it ros2-dev bash
source /opt/ros/humble/setup.bash
ros2 topic echo /alpamayo/answer
```

## Notes

- Hardware: Jetson AGX Orin 64GB
- Model: NVIDIA Alpamayo 1.5 10B
- ROS version: ROS 2 Humble
- Communication: TCP port 5000
- Average observed inference latency: ~4.5 seconds per two-frame question
- Model weights are stored locally and are not included in this repository.
