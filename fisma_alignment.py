"""Alineación V2 intacta, con recuperación adicional usando seis anclas FISMA.

Las fichas previas siguen la ruta V2. Los apoyos laterales solo se usan si
la alineación principal no recupera la retícula; nunca sustituyen respuestas.
"""
import itertools
import cv2
import numpy as np
import omr_align as v2
from sheet_pdf import ANCHOR_CENTERS_MM, SUPPORT_CENTERS_MM, point_to_canvas


def recovery_candidates(image):
    """Incluye apoyos de mitad de página; V2 prioriza solo las esquinas."""
    gray=v2._gray(image)
    side=min(gray.shape)
    blur=cv2.GaussianBlur(gray,(3,3),0)
    _,otsu=cv2.threshold(blur,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    adaptive=cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV,v2._adaptive_block(*gray.shape),10)
    candidates=[]
    for binary in (otsu,adaptive):
        contours,_=cv2.findContours(binary,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x,y,w,h=cv2.boundingRect(c)
            if min(w,h)<side*.012 or max(w,h)>side*.12 or not .5<w/h<2.: continue
            area=cv2.contourArea(c)
            if area/(w*h)<.42: continue
            if float((gray[y:y+h,x:x+w]<140).mean())<.35: continue
            p=(x+(w-1)/2,y+(h-1)/2,area,(w+h)/2)
            match=next((i for i,a in enumerate(candidates)
                        if (p[0]-a[0])**2+(p[1]-a[1])**2<36),None)
            if match is None:
                candidates.append(p)
            elif p[3]>candidates[match][3]:
                # Adaptive puede separar centro y borde de una guía sólida.
                # Conservar su silueta exterior, no el pequeño contorno interior.
                candidates[match]=p
    return candidates


def ring_coverage(warped):
    gray = v2._gray(warped)
    grid = v2.expected_omr_grid(15,5)
    circles = v2._hough_circles(gray,520,980,11,21)
    coords = np.asarray([p for row in v2.build_question_coords(grid,15).values() for p in row],np.float32)
    if not len(circles): return 0.
    distances = np.linalg.norm(coords[:,None,:]-circles[None,:,:2],axis=2).min(axis=1)
    return float((distances <= 11).mean())


def grouped_guides(image,work,scale,candidates):
    """Agrupa las cuatro formas de UNA ficha antes de construir la homografía.

    Las guías de otra ficha al borde de la foto no definen el encuadre.
    Tamaño, convexidad y proporción filtran hipótesis; las 75 burbujas las validan.
    """
    gray=v2._gray(work)
    groups={kind:[] for kind in ('solid','frame','ell','circle')}
    # El tamaño relativo entre las cuatro guías importa, no que estén en
    # las esquinas de la fotografía. Incluye guías pequeñas de ediciones previas.
    for candidate in sorted(candidates,key=lambda c:c[3],reverse=True):
        x,y,area,side=candidate
        kind,confidence=v2.classify_marker_at(gray,x,y,side)
        if confidence>=(5.5 if kind=='ell' else 7) and len(groups[kind])<12:
            groups[kind].append(candidate)
    if any(not pool for pool in groups.values()): return None
    hypotheses=[]
    image_area=work.shape[0]*work.shape[1]
    for quad in itertools.product(*(groups[k] for k in ('solid','frame','ell','circle'))):
        sizes=np.array([c[3] for c in quad])
        if sizes.max()>sizes.min()*1.5: continue
        src=np.float32([c[:2] for c in quad])
        if not cv2.isContourConvex(src) or cv2.contourArea(src,oriented=True)<=image_area*.12: continue
        sides=np.linalg.norm(np.roll(src,-1,axis=0)-src,axis=1)
        width=(sides[0]+sides[2])*.5
        height=(sides[1]+sides[3])*.5
        aspect=width/max(height,1)
        if not .48<aspect<.91: continue
        if not .7<sides[0]/max(sides[2],1)<1.43: continue
        if not .7<sides[1]/max(sides[3],1)<1.43: continue
        # Guías principales históricas de 5–10 mm con centros separados 128 mm.
        mm_size=float(np.median(sizes))/max(width,1)*128
        if not 4.0<mm_size<12.: continue
        penalty=abs(np.log(aspect/(128/190)))+float(sizes.std()/sizes.mean())
        hypotheses.append((penalty,src))
    hypotheses.sort(key=lambda h:h[0])
    best=None
    best_coverage=0.
    for _,src in hypotheses[:10]:
        h=cv2.getPerspectiveTransform(src/scale,v2.DST_TLTRBRBL)
        warped=cv2.warpPerspective(image,h,(v2.CANVAS_W,v2.CANVAS_H))
        coverage=ring_coverage(warped)
        if coverage>best_coverage:
            best_coverage=coverage
            best=(warped,dict(method='grouped_fiducials',roll=0,n_guides=4,
                ring_coverage=round(coverage,3),fiducials_ok=True,
                fiducial_kinds=['solid','frame','ell','circle'],n_marker_cands=len(candidates)))
        if coverage>=.96: break
    return best if best_coverage>=.72 else None


def warp_sheet_upright(image):
    primary = None
    primary_error = None
    try:
        primary,meta = v2.warp_sheet_upright(image)
        quality = ring_coverage(primary)
        meta['ring_coverage'] = round(quality,3)
        if quality >= .72:
            return primary,meta
    except ValueError as exc:
        primary_error = exc
        quality = 0.
    work,scale = v2._downscale(image,1600)
    candidates = recovery_candidates(work)
    grouped=grouped_guides(image,work,scale,candidates)
    if grouped is not None:
        print(f"[ALIGN FISMA] grupo de una ficha; retícula={grouped[1]['ring_coverage']:.0%}")
        return grouped
    paper = v2.find_paper_quad(work)
    best = None
    best_quality = quality
    if paper is not None and len(candidates)>=4:
        paper = v2._order_clockwise(paper)
        page = np.float32([point_to_canvas(0,210),point_to_canvas(148,210),
                           point_to_canvas(148,0),point_to_canvas(0,0)])
        anchors = {**ANCHOR_CENTERS_MM, **SUPPORT_CENTERS_MM}
        dst = np.float32([point_to_canvas(*p) for p in anchors.values()])
        source = np.float32([c[:2] for c in candidates])
        for roll in range(4):
            guess = cv2.getPerspectiveTransform(np.roll(paper,roll,axis=0),page)
            mapped = cv2.perspectiveTransform(source[None],guess)[0]
            distances = np.linalg.norm(dst[:,None,:]-mapped[None,:,:],axis=2)
            pairs = sorted((float(distances[i,j]),i,j) for i in range(len(dst)) for j in range(len(source)))
            assigned,used,src_pts,dst_pts = set(),set(),[],[]
            for distance,i,j in pairs:
                if distance>64 or i in assigned or j in used: continue
                assigned.add(i); used.add(j)
                src_pts.append(source[j]); dst_pts.append(dst[i])
            if len(assigned)<4: continue
            # Cuatro puntos con tres colineales no determinan una homografía.
            h,inliers = cv2.findHomography(np.float32(src_pts),np.float32(dst_pts),cv2.RANSAC,5.)
            if h is None or inliers is None or int(inliers.sum())<4: continue
            if not np.isfinite(h).all() or abs(np.linalg.det(h))<1e-10: continue
            full_h = h @ np.diag([scale,scale,1.])
            warped = cv2.warpPerspective(image,full_h,(v2.CANVAS_W,v2.CANVAS_H))
            score = ring_coverage(warped)
            if score>=.65 and score>best_quality+.08:
                best_quality = score
                best = warped,dict(method='six_guides_recovery',roll=roll,
                    n_guides=int(inliers.sum()),ring_coverage=round(score,3),
                    fiducials_ok=False,n_marker_cands=len(candidates))
    if best is not None:
        print(f"[ALIGN FISMA] recuperación con {best[1]['n_guides']} guías; retícula={best_quality:.0%}")
        return best
    if primary is not None and quality>=.45:
        return primary,meta
    if primary is not None:
        raise ValueError('No se pudo verificar la alineación de las burbujas. Fotografía la ficha completa, con las guías visibles y sin recortar los bordes.')
    raise primary_error or ValueError('No se pudo localizar la ficha completa.')
