import numpy as np
from scipy.spatial.transform import Rotation

R_C_T = np.array([
    [0.985,  0.110,  0.129],
    [0.100, -0.991,  0.085],
    [0.138, -0.071, -0.988]
])

R_B_T = np.array([
    [1,  0,  0],
    [0, -1,  0],
    [0,  0, -1]
])

R_T_C = R_C_T.T

R_B_C = R_B_T @ R_T_C

rpy = Rotation.from_matrix(R_B_C).as_euler('xyz', degrees=True)

print("Camera rotation matrix relative to base_link:")
print(R_B_C)

print(f"\nRoll:  {rpy[0]:.3f} degrees")
print(f"Pitch: {rpy[1]:.3f} degrees")
print(f"Yaw:   {rpy[2]:.3f} degrees")