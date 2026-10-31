"""Regresión del PDF real y flujo FISMA, sin usar datos de alumnos."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
import pymupdf
from reportlab.lib.units import mm

ROOT=Path(__file__).resolve().parents[1]
from sheet_pdf import build_sheet_pdf,get_omr_geometry,geometry_to_warped_canvas
from fisma_alignment import warp_sheet_upright
from omr_align import (detect_omr_grid,prepare_mark_maps,
                       bubble_features,snap_bubble_center,read_question_answer,build_question_coords)
from omr_processor import read_sheet_categories,save_claves_records,load_claves_records,normalize_reading_gray
import app as web

PROFILES=((15,5),)

def cfg(nq=15,na=5):
    return dict(num_questions=nq,num_alternatives=na,labels=dict(nombre="Apellidos y Nombres",
                colegio="Institución educativa",grado="Nivel de examen",procedencia="Procedencia"),
                branding=dict(title="I OLIMPIADA ESCOLAR REGIONAL DE FÍSICA 2025",logo=""),
                scoring=dict(buenas=10,malas=-1,blanco=0))

def photo(nq,na,answers=None,nivel=0,tipo=0,distort=False,missing_anchor=None):
    raw,_=build_sheet_pdf(settings=cfg(nq,na))
    doc=pymupdf.open(stream=raw,filetype="pdf")
    page=doc[0]
    g=get_omr_geometry(nq,na)
    coords=[(xs,y) for xs,ys in ((g['x_left_mm'],g['y_left_mm']),(g['x_right_mm'],g['y_right_mm'])) for y in ys]
    def fill(x,y,gray=.28,r=2.1):
        page.draw_circle((x*mm,(210-y)*mm),r*mm,color=None,fill=(gray,)*3)
    for i,answer in enumerate(answers or []):
        xs,y=coords[i]
        if answer=="X":
            for idx in (0,1): fill(xs[idx],y)
        elif answer in "ABCDE" and answer!="-":
            fill(xs["ABCDE".index(answer)],y,gray=.48 if i%3==0 else .28)
            # Borrado leve en una alternativa diferente.
            if i==3: fill(xs[("ABCDE".index(answer)+1)%na],y,gray=.86,r=1.8)
    for group,value in (("nivel",nivel),("tipo",tipo)):
        if value is not None:
            for idx in ((0,1) if value=="X" else (value,)):
                fill(*g['categories_mm'][group][idx],r=1.9)
    if missing_anchor:
        x,y=g['anchors_mm'][missing_anchor]
        page.draw_rect(pymupdf.Rect((x-5)*mm,(210-y-5)*mm,(x+5)*mm,(210-y+5)*mm),color=None,fill=(1,1,1))
    pix=page.get_pixmap(dpi=220,alpha=False)
    rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
    image=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    if distort:
        h,w=image.shape[:2]
        src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
        dst=np.float32([[65,35],[w+30,65],[w+55,h+55],[30,h+20]])
        image=cv2.warpPerspective(image,cv2.getPerspectiveTransform(src,dst),(w+100,h+100),borderValue=(205,205,205))
        gradient=np.linspace(.79,1.0,image.shape[1],dtype=np.float32)[None,:,None]
        image=np.clip(image.astype(np.float32)*gradient,0,255).astype(np.uint8)
        ok,jpg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,86])
        image=cv2.imdecode(jpg,cv2.IMREAD_COLOR)
    return image

def read(image,nq,na):
    with contextlib.redirect_stdout(io.StringIO()):
        warped,meta=warp_sheet_upright(image)
        gray=normalize_reading_gray(cv2.cvtColor(warped,cv2.COLOR_BGR2GRAY))
        with patch('omr_processor.load_settings_num_alternatives',return_value=na):
            grid=detect_omr_grid(gray,nq)
        maps=prepare_mark_maps(gray)
        answers=[]
        for coords in build_question_coords(grid,nq).values():
            feats=[]
            for letter,center in zip(grid['options'],coords):
                center=snap_bubble_center(gray,*center,grid['bubble_radius'],circ=grid.get('hough_circ'),search=4)
                f=bubble_features(gray,maps['adaptive'],center,grid['bubble_radius'],maps)
                feats.append((letter,f,center))
            answers.append(read_question_answer(feats)[0])
        cats=read_sheet_categories(gray,maps,nq,na)
    return answers,cats,meta,warped

class ReaderTests(unittest.TestCase):
    def test_shadow_does_not_turn_empty_bubbles_into_double_marks(self):
        expected=['-' if i%3==0 else 'ABCDE'[i%5] for i in range(15)]
        image=photo(15,5,expected,nivel=1,tipo=1)
        gradient=np.linspace(.53,.82,image.shape[0],dtype=np.float32)[:,None,None]
        image=np.clip(image.astype(np.float32)*gradient,0,255).astype(np.uint8)
        answers,cats,_,_=read(image,15,5)
        self.assertEqual(answers,expected)
        self.assertEqual((cats['nivel'],cats['tipo']),('Nivel VII','Privado'))

    def test_partial_neighbor_sheet_does_not_steal_the_guides(self):
        expected=['-' if i==0 else 'ABCDE'[i%5] for i in range(15)]
        image=photo(15,5,expected,nivel=1,tipo=1)
        h,w=image.shape[:2]
        strip=round(w*.22)
        for side in ('left','right'):
            canvas=np.full((h+100,w+strip+140,3),205,np.uint8)
            x=strip+100 if side=='left' else 40
            canvas[50:50+h,x:x+w]=image
            if side=='left': canvas[50:50+h,40:40+strip]=image[:,-strip:]
            else: canvas[50:50+h,x+w+60:x+w+60+strip]=image[:,:strip]
            for turn in (0,1,2,3):
                with self.subTest(side=side,turn=turn):
                    answers,cats,meta,_=read(np.ascontiguousarray(np.rot90(canvas,turn)),15,5)
                    self.assertEqual(answers,expected)
                    self.assertEqual((cats['nivel'],cats['tipo']),('Nivel VII','Privado'))
                    self.assertGreaterEqual(meta['ring_coverage'],.90)

    def test_recovery_when_one_corner_is_hidden(self):
        expected=['ABCDE'[i%5] for i in range(15)]
        for turn,corner in enumerate(('TL','TR','BL','BR')):
            with self.subTest(corner=corner):
                image=photo(15,5,expected,nivel=1,tipo=1,distort=True,missing_anchor=corner)
                answers,cats,meta,_=read(np.ascontiguousarray(np.rot90(image,turn)),15,5)
                self.assertEqual(answers,expected)
                self.assertEqual((cats['nivel'],cats['tipo']),('Nivel VII','Privado'))
                self.assertEqual(meta['method'],'six_guides_recovery')
                self.assertGreaterEqual(meta['n_guides'],4)

    def test_plain_paper_cannot_be_graded_as_a_sheet(self):
        with self.assertRaises(ValueError):
            warp_sheet_upright(np.full((1130,800,3),240,np.uint8))

    def test_v2_algorithms_are_identical(self):
        import hashlib
        original=json.loads((ROOT/'BASE_V2.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((ROOT/'omr_align.py').read_bytes()).hexdigest(),original['omr_align_sha256'])

    def test_actual_pdf_geometry(self):
        for nq,na in PROFILES:
            with self.subTest(nq=nq,na=na):
                raw,_=build_sheet_pdf(settings=cfg(nq,na))
                doc=pymupdf.open(stream=raw,filetype='pdf')
                p=doc[0]
                self.assertAlmostEqual(p.rect.width/mm,148,places=3)
                self.assertAlmostEqual(p.rect.height/mm,210,places=3)
                text=p.get_text()
                self.assertIn('LLENADO CON LÁPIZ',text)
                self.assertIn('Usa lápiz 2B.',text)
                self.assertIn('Nivel VII',text)
                rings=[d for d in p.get_drawings() if len(d['items'])==4 and all(i[0]=='c' for i in d['items']) and abs(d['rect'].width/mm-5.5)<.05]
                self.assertEqual(len(rings),nq*na)
                g=get_omr_geometry(nq,na)
                self.assertEqual(g['anchor_sizes_mm'],dict.fromkeys(('TL','TR','BL','BR'),8.0))
                self.assertEqual(g['anchors_mm'],{'TL':(10.,200.),'TR':(138.,200.),'BL':(10.,10.),'BR':(138.,10.)})
                # Medida del PDF final, no solo de las constantes del lector.
                guides=p.get_drawings()[:6]
                for index in (0,1,3):
                    self.assertAlmostEqual(guides[index]['rect'].width/mm,8.,places=3)
                    self.assertAlmostEqual(guides[index]['rect'].height/mm,8.,places=3)
                ell=guides[4]['rect'] | guides[5]['rect']
                self.assertAlmostEqual(ell.width/mm,8.,places=3)
                self.assertAlmostEqual(ell.height/mm,8.,places=3)
                expected=[(x,y) for xs,ys in ((g['x_left_mm'],g['y_left_mm']),(g['x_right_mm'],g['y_right_mm'])) for y in ys for x in xs]
                for drawing,(x,y) in zip(rings,expected):
                    center=(drawing['rect'].tl+drawing['rect'].br)/2
                    self.assertAlmostEqual(center.x/mm,x,places=3)
                    self.assertAlmostEqual(210-center.y/mm,y,places=3)

    def test_profiles_rotations_and_perspective(self):
        for nq,na in PROFILES:
            expected=['-' if i%7==0 else 'X' if i%7==1 else 'ABCDE'[i%na] for i in range(nq)]
            image=photo(nq,na,expected,nivel=1,tipo=1,distort=True)
            for turn in range(4):
                with self.subTest(nq=nq,na=na,rotation=turn*90):
                    actual,cats,meta,_=read(np.ascontiguousarray(np.rot90(image,turn)),nq,na)
                    self.assertEqual(actual,expected)
                    self.assertEqual((cats['nivel'],cats['tipo']),('Nivel VII','Privado'))

    def test_empty_sheet_and_selector_combinations(self):
        for lev,typ in ((0,0),(0,1),(1,0),(1,1),(None,None),('X','X')):
            with self.subTest(nivel=lev,tipo=typ):
                ans,cats,_,_=read(photo(15,5,nivel=lev,tipo=typ),15,5)
                self.assertEqual(ans,['-']*15)
                self.assertEqual(cats['nivel'],None if lev in (None,'X') else ('Nivel VI','Nivel VII')[lev])
                self.assertEqual(cats['tipo'],None if typ in (None,'X') else ('Publico','Privado')[typ])
                if lev=='X': self.assertEqual(cats['nivel_estado'],'doble')

    def test_small_markers_1000px_and_legacy_guides(self):
        # Conserva el camino rápido por formas para guías nuevas y fichas previas.
        for size in (5.,6.,8.,10.):
            with patch('sheet_pdf.MARKER_SIZE_MM',size), patch('sheet_pdf.ANCHOR_SIZES_MM',dict.fromkeys(('TL','TR','BL','BR'),size)):
                for turn,(nq,na) in enumerate(PROFILES):
                    expected=['ABCDE'[i%na] for i in range(nq)]
                    image=photo(nq,na,expected,nivel=1,tipo=0,distort=True)
                    h,w=image.shape[:2]
                    image=cv2.resize(image,(round(w*1000/max(h,w)),round(h*1000/max(h,w))),interpolation=cv2.INTER_AREA)
                    image=np.ascontiguousarray(np.rot90(image,turn))
                    with self.subTest(size=size,nq=nq,na=na,rotation=turn*90):
                        actual,cats,meta,_=read(image,nq,na)
                        self.assertEqual(actual,expected)
                        self.assertEqual((cats['nivel'],cats['tipo']),('Nivel VII','Publico'))
                        self.assertTrue(meta['fiducials_ok'])

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.base=Path(self.tmp.name)
        self.old=os.getcwd()
        os.chdir(self.base)
        (self.base/'settings_config.json').write_text(json.dumps(cfg()),encoding='utf-8')
        self.patches=[]
        for name,value in dict(BASE_DIR=str(self.base),CONFIG_PATH=str(self.base/'claves.xlsx'),
             REPORT_PATH=str(self.base/'resultados.xlsx'),UPLOAD_FOLDER=str(self.base/'uploads'),
             PROCESSED_FOLDER=str(self.base/'static/processed'),BATCH_FOLDER=str(self.base/'static/processed/batches'),
             PACK_FOLDER=str(self.base/'uploads/packs'),BRANDING_DIR=str(self.base/'static/branding'),
             BRANDING_LOGO=str(self.base/'static/branding/logo.png')).items():
            patcher=patch.object(web,name,value)
            patcher.start()
            self.patches.append(patcher)
        for name in (web.UPLOAD_FOLDER,web.PROCESSED_FOLDER,web.BATCH_FOLDER,web.PACK_FOLDER): Path(name).mkdir(parents=True,exist_ok=True)
        web.initialize_workspace()
        self.client=web.app.test_client()

    def tearDown(self):
        for patcher in reversed(self.patches): patcher.stop()
        os.chdir(self.old)
        self.tmp.cleanup()

    def keys(self,nq=15,na=5):
        return [{'Salon':lev,'Curso':typ,**{f'Q{i+1}':'ABCDE'[i%na] for i in range(nq)}}
                for lev in ('Nivel VI','Nivel VII') for typ in ('Publico','Privado')]

    def test_key_saving_validation_and_excel_roundtrip(self):
        self.assertFalse(self.client.get('/get_key_meta?salon=Nivel%20VI&curso=Publico').json['valid'])
        rows=self.keys()
        self.assertEqual(self.client.post('/save_keys',json=rows).status_code,200)
        bad={**rows[0],'Q1':''}
        self.assertEqual(self.client.post('/save_keys',json=[bad]).status_code,400)
        raw=self.client.get('/download_keys_excel').data
        self.assertEqual(self.client.post('/import_keys',data={'file':(io.BytesIO(raw),'Claves.xlsx')}).status_code,200)
        self.assertEqual(len(self.client.get('/get_keys').json),4)
        save_claves_records(web.CONFIG_PATH,[],15)
        self.assertEqual(self.client.post('/import_keys',data={'file':(io.BytesIO(raw),'Claves.xlsx')}).json['count'],4)
        identity=lambda records:{(r['Salon'],r['Curso']):r for r in records}
        self.assertEqual(identity(load_claves_records(web.CONFIG_PATH)),identity(rows))

    def test_switch_profiles_and_validate_keys_against_alternatives(self):
        for nq,na in PROFILES:
            with self.subTest(nq=nq,na=na):
                result=self.client.post('/save_settings',json={'num_questions':nq,'num_alternatives':na})
                self.assertEqual(result.status_code,200,result.json)
                geometry=self.client.get('/get_template').json
                self.assertEqual(len(geometry['omr_questions']['options']),na)
                self.assertEqual(geometry['omr_questions']['right_column']['q_range'][1],nq)
                self.assertEqual(self.client.post('/save_keys',json=self.keys(nq,na)).status_code,200)
                self.assertEqual(self.client.get('/get_key_meta?salon=Nivel%20VI&curso=Publico').json['num_questions'],nq)
                self.assertEqual(self.client.get('/sheet_preview.png').status_code,200)
        bad={**self.keys()[0],'Q1':'F'}
        self.assertEqual(self.client.post('/save_keys',json=[bad]).status_code,400)
        self.assertEqual(self.client.post('/save_settings',json={'num_questions':18}).status_code,400)
        self.assertEqual(self.client.post('/save_settings',json={'num_questions':20}).status_code,400)
        self.assertEqual(self.client.post('/save_settings',json={'num_alternatives':4}).status_code,400)

    def test_logo_upload_replaces_placeholder_preserving_geometry(self):
        from PIL import Image
        raw=io.BytesIO()
        Image.new('RGB',(600,180),(25,70,150)).save(raw,format='PNG')
        response=self.client.post('/upload_logo',data={'logo':(io.BytesIO(raw.getvalue()),'logo.png')})
        self.assertEqual(response.status_code,200,response.json)
        pdf=self.client.get('/download_sheet_pdf').data
        p=pymupdf.open(stream=pdf,filetype='pdf')[0]
        self.assertEqual(len(p.get_images()),1)
        self.assertNotIn('FISMA\nFÍSICA',p.get_text())
        self.assertEqual(self.client.post('/delete_logo').status_code,200)
        self.assertEqual(len(pymupdf.open(stream=self.client.get('/download_sheet_pdf').data,filetype='pdf')[0].get_images()),0)

    def test_auto_categories_grading_batch_pdf_excel_and_restart(self):
        self.client.post('/save_keys',json=self.keys())
        expected=['ABCDE'[i%5] for i in range(15)]
        images=[]
        for lev,typ in ((0,0),(1,1)):
            ok,encoded=cv2.imencode('.jpg',photo(15,5,expected,nivel=lev,tipo=typ,distort=True))
            images.append((io.BytesIO(encoded.tobytes()),f'{lev}_{typ}.jpg'))
        result=self.client.post('/batch_scan',data={'images':images,'salon':'Nivel VI','curso':'Publico','read_categories':'1'})
        self.assertEqual(result.status_code,200,result.json)
        data=result.json
        self.assertEqual(data['errors'],[])
        self.assertEqual(data['processed'],2)
        self.assertEqual([r['buenas'] for r in data['results']],[15,15])
        self.assertEqual([r['salon'] for r in data['results']],['Nivel VI','Nivel VII'])
        self.assertEqual([r['curso'] for r in data['results']],['Publico','Privado'])
        pdf=self.client.get(data['download_pdf_url'])
        self.assertEqual(pdf.status_code,200)
        self.assertEqual(len(pymupdf.open(stream=pdf.data,filetype='pdf')),3)
        self.assertEqual(self.client.get(data['download_pngs_url']).status_code,200)
        from openpyxl import load_workbook
        wb=load_workbook(io.BytesIO(self.client.get('/download_report').data))
        self.assertEqual(set(wb.sheetnames),{'Detalle General','Nivel VI','Nivel VII'})
        self.assertIn('Nivel de examen',[c.value for c in wb['Detalle General'][1]])
        wb.close()
        web.initialize_workspace()
        self.assertEqual(len(self.client.get('/get_registry').json),2)
        self.assertTrue(self.client.get('/get_key_meta?salon=Nivel%20VII&curso=Privado').json['valid'])

    def test_blank_categories_require_explicit_manual_mode(self):
        self.client.post('/save_keys',json=self.keys())
        ok,image=cv2.imencode('.jpg',photo(15,5,nivel=None,tipo=None))
        form={'salon':'Nivel VI','curso':'Publico','image':(io.BytesIO(image.tobytes()),'blanco.jpg')}
        response=self.client.post('/scan',data=form)
        self.assertEqual(response.status_code,400,response.json)
        self.assertIn('selección manual',response.json['error'])
        self.assertTrue(response.json['preview_url'].startswith('/static/processed/failed_'))
        response=self.client.post('/scan',data={'salon':'Nivel VI','curso':'Publico','read_categories':'0','image':(io.BytesIO(image.tobytes()),'manual.jpg')})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['en_blanco'],15)

    def test_failed_batch_returns_photo_preview_without_invented_grade(self):
        ok,image=cv2.imencode('.jpg',photo(15,5,nivel=None,tipo=None))
        response=self.client.post('/batch_scan',data={'salon':'Nivel VI','curso':'Publico',
            'images':[(io.BytesIO(image.tobytes()),'observacion.jpg')]})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['processed'],0)
        self.assertEqual(len(response.json['errors']),1)
        error=response.json['errors'][0]
        self.assertIn('preview_url',error)
        self.assertTrue(list(Path(web.BATCH_FOLDER).rglob('failed_*.jpg')))
        self.assertEqual(self.client.get('/get_registry').json,[])

    def test_zip_folder_categories(self):
        from omr_pack import parse_rel_path,discover_lots
        self.assertEqual(parse_rel_path('Lote/Nivel VII/Público/foto.jpg'),('Nivel VII','Publico'))
        self.assertIsNone(parse_rel_path('Sec 5/Matematica/foto.jpg'))
        for lev,typ in (('Nivel VI','Publico'),('Nivel VII','Privado')):
            path=self.base/lev/typ
            path.mkdir(parents=True)
            (path/'foto.jpg').write_bytes(b'test')
        self.assertEqual(len(discover_lots(str(self.base))),2)

    def test_zip_ingest_and_grade_by_folder_name(self):
        import zipfile
        self.client.post('/save_keys',json=self.keys())
        ok,image=cv2.imencode('.jpg',photo(15,5,nivel=None,tipo=None))
        packed=io.BytesIO()
        with zipfile.ZipFile(packed,'w') as z:
            z.writestr('FISMA/Nivel VI/Público/foto.jpg',image.tobytes())
            z.writestr('FISMA/Nivel VII/Privado/foto.jpg',image.tobytes())
        ingested=self.client.post('/pack_ingest',data={'pack':(io.BytesIO(packed.getvalue()),'Lote.zip')})
        self.assertEqual(ingested.status_code,200,ingested.json)
        self.assertEqual(ingested.json['total'],2)
        for lot in ingested.json['lots']:
            response=self.client.post('/pack_grade_lot',data={'pack_id':ingested.json['pack_id'],
                'salon':lot['salon'],'curso':lot['curso'],'read_categories':'0'})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['processed'],1)
            self.assertEqual(response.json['errors'],[])
            self.assertEqual(response.json['results'][0]['en_blanco'],15)

    def test_android_pack_profile_must_match_web_template(self):
        import zipfile
        packed=io.BytesIO()
        with zipfile.ZipFile(packed,'w') as z:
            z.writestr('manifest.json',json.dumps({'format':'lectoraomr-pack','app':'Fisma OMR',
                'sheet':{'questions':20,'alternatives':5,'guide_mm':6}}))
            z.writestr('Nivel VI/Publico/foto.jpg',b'synthetic')
        result=self.client.post('/pack_ingest',data={'pack':(io.BytesIO(packed.getvalue()),'Fisma.zip')})
        self.assertEqual(result.status_code,409,result.json)
        self.assertIn('error',result.json)

if __name__=='__main__': unittest.main()
