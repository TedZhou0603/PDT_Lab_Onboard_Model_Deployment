import argparse
from pathlib import Path
import cv2
import numpy as np
from camera_calibration.calibrator import MonoCalibrator, ChessboardInfo

K = np.array([[3266.81912, 0, 1006.36586], [0, 3287.87229, 751.399516], [0, 0, 1]], dtype=np.float64)
D = np.array([-0.23367138, 0.12731275, 0.00047681, -0.00048044, 0.0], dtype=np.float64)

def main():
    parser = argparse.ArgumentParser(description='Validate fixed intrinsics and visualize corner residuals.')
    parser.add_argument('folder', nargs='?', default='validation_images_new')
    parser.add_argument('--output', default='validation_debug')
    args = parser.parse_args()
    folder, output = Path(args.folder), Path(args.output)
    if folder.resolve() == output.resolve():
        parser.error('Output must differ from input folder')
    paths = sorted(p for p in folder.glob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg','.pgm','.bmp','.tif','.tiff'})
    if not paths:
        parser.error(f'No images found in {folder}')
    output.mkdir(parents=True, exist_ok=True)
    board = ChessboardInfo(pattern='chessboard', n_cols=11, n_rows=9, dim=0.041275)
    detector = MonoCalibrator([board])
    total_sq = 0.0
    total_points = accepted = 0
    for path in paths:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None or img.shape != (1544, 2064):
            print(f'{path.name}: skipped (unreadable or wrong resolution)')
            continue
        _, corners, _, _, detected_board, _ = detector.downsample_and_detect(img)
        if corners is None:
            print(f'{path.name}: skipped (no checkerboard detected)')
            continue
        cols, rows = detected_board.n_cols, detected_board.n_rows
        if (cols, rows) not in [(11,9),(9,11)] or len(corners) != 99:
            print(f'{path.name}: skipped (unexpected board dimensions)')
            continue
        points = np.zeros((99,3), np.float32)
        points[:,:2] = np.mgrid[0:cols,0:rows].T.reshape(-1,2)*0.041275
        ok, rvec, tvec = cv2.solvePnP(points, corners, K, D, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            print(f'{path.name}: skipped (pose estimation failed)')
            continue
        projected, _ = cv2.projectPoints(points,rvec,tvec,K,D)
        a = corners.reshape(-1,2).astype(np.float64)
        b = projected.reshape(-1,2).astype(np.float64)
        errors = np.linalg.norm(a-b,axis=1)
        sq = float(np.sum(errors**2))
        rms = np.sqrt(sq/len(points))
        total_sq += sq
        total_points += len(points)
        accepted += 1
        canvas = cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
        for i,(det,proj,err) in enumerate(zip(a,b,errors)):
            p,q = tuple(np.rint(det).astype(int)),tuple(np.rint(proj).astype(int))
            if err > 2:
                cv2.line(canvas,p,q,(0,255,255),2,cv2.LINE_AA)
            cv2.circle(canvas,p,5,(0,255,0),2,cv2.LINE_AA)
            cv2.circle(canvas,q,2,(0,0,255),-1,cv2.LINE_AA)
            if err > 2:
                cv2.putText(canvas,f'{i}: {err:.1f}',(p[0]+7,p[1]-7),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,255,255),1,cv2.LINE_AA)
        count = int(np.sum(errors>2))
        cv2.rectangle(canvas,(0,0),(min(1200,canvas.shape[1]-1),90),(0,0,0),-1)
        cv2.putText(canvas,f'{path.name} | RMS {rms:.3f} px | max {errors.max():.2f} px | >2 px: {count}/99',(15,32),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2,cv2.LINE_AA)
        cv2.putText(canvas,'Green: detected | Red: projected | Yellow: residual > 2 px (index: error)',(15,68),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),1,cv2.LINE_AA)
        dest = output / f'{path.name}_debug.png'
        if not cv2.imwrite(str(dest),canvas):
            raise OSError(f'Could not write {dest}')
        print(f'{path.name}: RMS = {rms:.4f} px; max = {errors.max():.2f} px; >2 px = {count}/99')
    print(f'\nValidated: {accepted}/{len(paths)} images; skipped: {len(paths)-accepted}')
    if not total_points:
        raise SystemExit('No valid images; RMS unavailable.')
    print(f'Overall validation RMS: {np.sqrt(total_sq/total_points):.6f} px')
    print(f'Annotated images: {output.resolve()}')
    print('Camera matrix and distortion held fixed. No calibration files modified.')

if __name__ == '__main__':
    main()