
To install the needed packages use:
chmod +x install_camera_tools.sh
./install_camera_tools.sh

How to use: 

source /opt/ros/humble/setup.bash


# Camera calibration

ros2 run camera_calibration cameracalibrator \
  --size 8x6 \
  --square 0.025 \
  --ros-args \
  -r image:=/image_raw \
  -r camera:=/camera

# Image Rectification 
ros2 run image_proc rectify_node --ros-args \
  -r image:=/image_raw \
  -r camera_info:=/camera_info \
  -r image_rect:=/image_rect

# April Tag 

ros2 run apriltag_ros apriltag_node --ros-args \
  --params-file tags.yaml \
  -r image_rect:=/image_rect \
  -r camera_info:=/camera_info
