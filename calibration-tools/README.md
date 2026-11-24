incase you forget list:

# Turn on camera with current camera intrinisc properties
ros2 run vimbax_camera vimbax_camera_node \
  --ros-args \
  -p camera_info_url:=file:///home/dev/Desktop/ros2_bridge/mako_calibration.yaml

# Start Image Rectification 
ros2 run image_proc rectify_node --ros-args \
  -r image:=/image_raw \
  -r camera_info:=/camera_info \
  -r image_rect:=/image_rect

  # Start April Tag 

  ros2 run apriltag_ros apriltag_node --ros-args \
  -r image_rect:=/image_rect \
  -r camera_info:=/camera_info \
  -p family:=25h9 \
  -p size:=0.1524


  # To view the activity of the camera
  ros2 run rqt_image_view rqt_image_view

# To Run the camera calibration package
  ros2 run camera_calibration cameracalibrator \
  --size 11x9 \
  --square 0.041275 \
  image:=/image_raw \
  camera:=/

  RMS reprojection error after filtering: 0.972117 pixels

Location for packages: 
  /opt/ros/humble/lib/camera_calibration/
  /opt/ros/humble/lib/apriltag_ros/
  /opt/ros/humble/lib/image_proc/

  ros2 topic dev@dev-2204:~$ ros2 topic echo --once /detections
header:
  stamp:
    sec: 1758
    nanosec: 699329600
  frame_id: vimbax_camera_DEV_000F315E05D0
detections:
- family: tag25h9
  id: 0
  hamming: 0
  goodness: 0.0
  decision_margin: 139.38116455078125
  centre:
    x: 1260.2959079617278
    y: 957.756137456746
  corners:
  - x: 1157.0052490234377
    y: 1036.47119140625
  - x: 1338.8199462890625
    y: 1063.565673828125
  - x: 1364.1444091796875
    y: 878.615966796875
  - x: 1182.5828857421877
    y: 853.0394287109374
  homography:
  - 85.8745326277342
  - -14.300218892480173
  - 1260.2959079617278
  - 9.391142359526937
  - 90.89749589617645
  - 957.756137456746
  - -0.003942006361888132
  - -0.0012489266021328208
  - 1.0
---
dev@dev-2204:~$ 

