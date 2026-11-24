import argparse
from pathlib import Path
import cv2
import numpy as np
from camera_calibration.calibrator import MonoCalibrator, ChessboardInfo

K = np.array([
    [3266.81912, 0, 1006.36586],
    [0, 3287.87229, 751.399516],
    [0, 0, 1]
], dtype=np.float64)

D = np.array([
    -0.23367138,
     0.12731275,
     0.00047681,
    -0.00048044,
     0.0
], dtype=np.float64)
def main():
    parser = argparse.ArgumentParser(description='Validate fixed camera intrinsics on fresh checkerboard images.')
    parser.add_argument('folder', nargs='?', default='validation_images')
    args = parser.parse_args()
    folder = Path(args.folder)
    paths = sorted(p for p in folder.glob('*') if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.pgm', '.bmp', '.tif', '.tiff'})
    if not paths:
        parser.error(f'No images found in {folder}')
    board = ChessboardInfo(pattern='chessboard', n_cols=11, n_rows=9, dim=0.041275)
    detector = MonoCalibrator([board])
    obj = np.zeros((99, 3), np.float32)
    obj[:, :2] = np.mgrid[0:11, 0:9].T.reshape(-1, 2) * 0.041275
    total_sq = 0.0
    total_points = 0
    accepted = 0
    for path in paths:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None or img.shape != (1544, 2064):
            print(f'{path.name}: skipped (unreadable or wrong resolution)')
            continue
        _, corners, _, _, detected_board, _ = detector.downsample_and_detect(img)
        if corners is None:
            print(f'{path.name}: skipped (no checkerboard detected)')
            continue
        # Respect the orientation returned by the ROS detector.
        cols, rows = detected_board.n_cols, detected_board.n_rows
        if (cols, rows) not in [(11, 9), (9, 11)] or len(corners) != 99:
            print(f'{path.name}: skipped (unexpected board dimensions)')
            continue
        points = obj if (cols, rows) == (11, 9) else np.column_stack((np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)*0.041275, np.zeros(99))).astype(np.float32)
        ok, rvec, tvec = cv2.solvePnP(points, corners, K, D, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            print(f'{path.name}: skipped (pose estimation failed)')
            continue
        projected, _ = cv2.projectPoints(points, rvec, tvec, K, D)
        residual = corners.reshape(-1, 2) - projected.reshape(-1, 2)
        sq = float(np.sum(residual.astype(np.float64)**2))
        total_sq += sq
        total_points += len(points)
        accepted += 1
        print(f'{path.name}: RMS = {np.sqrt(sq/len(points)):.4f} px')
    print(f'\nValidated: {accepted}/{len(paths)} images; skipped: {len(paths)-accepted}')
    if not total_points:
        raise SystemExit('No valid images; RMS unavailable.')
    print(f'Overall validation RMS: {np.sqrt(total_sq/total_points):.6f} px')
    print('Camera matrix and distortion were held fixed. No calibration files modified.')

if __name__ == '__main__':
    main()