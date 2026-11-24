import argparse
import tarfile
import cv2
import numpy as np
from camera_calibration.calibrator import MonoCalibrator, ChessboardInfo

p = argparse.ArgumentParser()
p.add_argument('--archive', default='/tmp/calibrationdata.tar.gz')
p.add_argument('--target', type=float, default=1.0)
p.add_argument('--min-images', type=int, default=20)
a = p.parse_args()
if a.min_images < 3 or a.target <= 0:
    p.error('Require at least 3 images and a positive target')
board = ChessboardInfo(pattern='chessboard', n_cols=11, n_rows=9, dim=0.041275)
cal = MonoCalibrator([board])
samples = []
size = None
with tarfile.open(a.archive, 'r:*') as archive:
    for m in sorted(archive.getmembers(), key=lambda m: m.name):
        if not m.isfile() or not m.name.split('/')[-1].startswith('left') or not m.name.lower().endswith(('.png', '.pgm')):
            continue
        img = cv2.imdecode(np.frombuffer(archive.extractfile(m).read(), np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        s = (img.shape[1], img.shape[0])
        if size is not None and s != size:
            raise ValueError('Mixed image resolutions')
        size = s
        _, corners, _, ids, detected_board, _ = cal.downsample_and_detect(img)
        if corners is None:
            print(m.name, 'not detected')
            continue
        samples.append((m.name, corners))
        print(m.name, 'detected')
if len(samples) < a.min_images:
    raise RuntimeError(f'Only {len(samples)} detected; minimum is {a.min_images}')
obj = np.zeros((99, 3), np.float32)
obj[:, :2] = np.mgrid[0:11, 0:9].T.reshape(-1, 2) * 0.041275

def fit(items):
    rms, K, D, rs, ts = cv2.calibrateCamera([obj.copy() for _ in items], [c for _, c in items], size, None, None, flags=cv2.CALIB_FIX_K3)
    errors = []
    for (_, c), r, t in zip(items, rs, ts):
        q, _ = cv2.projectPoints(obj, r, t, K, D)
        errors.append(float(np.sqrt(np.mean(np.sum((q.reshape(-1, 2)-c.reshape(-1, 2))**2, axis=1)))))
    return rms, K, D, np.array(errors)

def coverage(items):
    centers = np.array([c.reshape(-1,2).mean(axis=0) for _, c in items]) / np.array(size)
    bins = np.clip((centers*3).astype(int), 0, 2)
    return len(set(map(tuple, bins)))

active = samples.copy()
removed = []
initial = None
while True:
    rms, K, D, errors = fit(active)
    if initial is None:
        initial = rms
    print(f'\n{len(active)} images: RMS = {rms:.6f} px; board-center coverage = {coverage(active)}/9 cells')
    if rms <= a.target or len(active) <= a.min_images:
        break
    i = int(np.argmax(errors))
    name, corners = active.pop(i)
    removed.append((name, corners))
    print(f'Removing {name}: {errors[i]:.4f} px')
print(f'\nInitial RMS: {initial:.6f} px\nFinal RMS: {rms:.6f} px\nRetained: {len(active)}; removed: {len(removed)}')
print('Target reached' if rms <= a.target else 'Stopped at minimum image count; target not reached')
print('Camera matrix:\n', K)
print('Distortion:', D.ravel())
print('\nRetained images:')
for (name, _), e in zip(active, errors):
    print(f'{name}: {e:.4f} px')
if removed:
    print('\nRejected images evaluated with final intrinsics (not independent validation):')
    for name, c in removed:
        ok, r, t = cv2.solvePnP(obj, c, K, D)
        if ok:
            q, _ = cv2.projectPoints(obj, r, t, K, D)
            e = np.sqrt(np.mean(np.sum((q.reshape(-1,2)-c.reshape(-1,2))**2, axis=1)))
            print(f'{name}: {e:.4f} px')
print('Validate on new images; low training RMS alone does not establish accuracy.')