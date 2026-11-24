incase you forget list:

Turn on camera with current camera intrinisc properties
ros2 run vimbax_camera vimbax_camera_node \
  --ros-args \
  -p camera_info_url:=file:///home/dev/Desktop/ros2_bridge/mako_calibration.yaml

Start Image Rectification 
ros2 run image_proc rectify_node --ros-args \
  -r image:=/image_raw \
  -r camera_info:=/camera_info \
  -r image_rect:=/image_rect

  Start April Tag 

  ros2 run apriltag_ros apriltag_node --ros-args \
  -r image_rect:=/image_rect \
  -r camera_info:=/camera_info \
  -p family:=25h9 \
  -p size:=0.1524


  To view the activity of the camera
  ros2 run rqt_image_view rqt_image_view
  
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
