"""Ficha FISMA A5. Una sola geometría para PDF, lector V2 y calificación."""
from __future__ import annotations
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A5
from domain import sector, sector_label

OMR_PROFILE_VERSION = "FISMA-A5-2026.5-8mm-6guias"
PAGE_W_MM, PAGE_H_MM = 148., 210.
CANVAS_W, CANVAS_H = 800, 1130
# Más área negra sin mover centros ni burbujas; dos apoyos laterales redundantes.
MARKER_INSET_MM, MARKER_SIZE_MM = 6., 8.
ANCHOR_KINDS = {"TL":"solid", "TR":"frame", "BL":"circle", "BR":"ell"}
ANCHOR_CENTERS_MM = {"TL":(10.,200.),"TR":(138.,200.),"BL":(10.,10.),"BR":(138.,10.)}
ANCHOR_SIZES_MM = dict.fromkeys(ANCHOR_KINDS, MARKER_SIZE_MM)
MARKER_DST = {"TL":(40,40),"TR":(760,40),"BL":(40,1090),"BR":(760,1090)}
SUPPORT_CENTERS_MM = {"ML": (10.,105.), "MR": (138.,105.)}
SUPPORT_SIZE_MM = 4.

THEME = dict(primary=HexColor("#2563eb"), primary_dark=HexColor("#1d4ed8"),
             primary_light=HexColor("#60a5fa"), border=HexColor("#93c5fd"),
             zebra=HexColor("#eff6ff"), header_bg=HexColor("#f5f9ff"),
             label=HexColor("#2563eb"), bubble_text=HexColor("#cbd5e1"),
             muted=HexColor("#64748b"), hint=HexColor("#cbd5e1"))

def resolve_theme(curso=None):
    value = sector(curso) or "Publico"
    return {**THEME,"id":value,"title":sector_label(value),"badge":"FISMA · FÍSICA",
            "filename":"ficha_fisma_a5.pdf"}

def validate_profile(nq, na):
    nq, na = int(nq), int(na)
    if (nq,na) != (15,5):
        raise ValueError("Fisma OMR usa un único formato: 15 preguntas y 5 alternativas (A–E).")
    return nq, na

def get_omr_geometry(num_questions=15, num_alternatives=5):
    nq,na = validate_profile(num_questions,num_alternatives)
    mid = (nq+1)//2
    row_h = 70./mid
    xoffs = [13+i*8.6 for i in range(5)] if na == 5 else [14+i*11.4 for i in range(4)]
    ys = [210-(108+(i+.5)*row_h) for i in range(mid)]
    # Todas las cajas en mm con origen PDF inferior izquierdo.
    return dict(profile=OMR_PROFILE_VERSION,anchors_mm=dict(ANCHOR_CENTERS_MM),
                anchor_sizes_mm=dict(ANCHOR_SIZES_MM),anchor_kinds=dict(ANCHOR_KINDS),
                num_questions=nq,num_alternatives=na,options=list("ABCDE"[:na]),
                x_left_mm=[17+x for x in xoffs],x_right_mm=[76+x for x in xoffs],
                y_left_mm=ys,y_right_mm=ys[:nq-mid],row_h_mm=row_h,
                bubble_diameter_mm=5.5,bubble_gap_mm=(8.6 if na==5 else 11.4)-5.5,
                questions_top_mm=102.,questions_bottom_mm=32.,
                left_col_x_mm=17.,right_col_x_mm=76.,col_w_mm=55.,col_gap_mm=4.,
                pad_x_mm=17.,pad_top_mm=18.,pad_bottom_mm=12.5,
                header_h_mm=30.,footer_h_mm=17.,compact=nq==20,
                header_box_mm=(17.,137.,114.,30.),footer_box_mm=(17.,12.5,114.,17.),
                nombre_box_mm=(20.,153.7,108.,8.),colegio_box_mm=(20.,139.9,108.,8.),
                grado_box_mm=(17.,116.,55.,17.),procedencia_box_mm=(76.,116.,55.,17.),
                numero_orden_box_mm=(51.,12.5,21.5,7.),hora_entrega_box_mm=(75.5,12.5,21.5,7.),
                score_box_mm=(112.,172.,19.,14.2),
                categories_mm={"nivel":[(22.,121.3),(48.,121.3)],
                               "tipo":[(81.,121.3),(106.,121.3)]},category_diameter_mm=5.)

def point_to_canvas(x,y):
    # Mismo mapeo por centros de anclas de V2, sin deformar los círculos del PDF.
    return (int(round(40+(x-10)*720/128)),int(round(40+(200-y)*1050/190)))

def box_to_canvas(box):
    x,y,w,h=box
    x1,y1=point_to_canvas(x,y+h)
    x2,y2=point_to_canvas(x+w,y)
    return dict(x=x1,y=y1,w=x2-x1,h=y2-y1)

def geometry_to_warped_canvas(g):
    ys = [[point_to_canvas(10,y)[1] for y in g[key]] for key in ("y_left_mm","y_right_mm")]
    fields = {name:box_to_canvas(g[name+"_box_mm"]) for name in
              ("header","footer","nombre","colegio","grado","procedencia")}
    fields.update(numero_orden_box=box_to_canvas(g["numero_orden_box_mm"]),
                  hora_entrega_box=box_to_canvas(g["hora_entrega_box_mm"]))
    return dict(options=g["options"],x_left=[point_to_canvas(x,200)[0] for x in g["x_left_mm"]],
                x_right=[point_to_canvas(x,200)[0] for x in g["x_right_mm"]],
                y_rows_left=ys[0],y_rows_right=ys[1],y_start_left=ys[0][0],y_start_right=ys[1][0],
                y_step=g["row_h_mm"]*1050/190,bubble_radius=round(g["bubble_diameter_mm"]*720/128/2),
                method="profile_"+g["profile"],profile=g["profile"],anchor_kinds=g["anchor_kinds"],
                ocr_fields=fields,compact=g["compact"],num_questions=g["num_questions"],
                num_alternatives=g["num_alternatives"],
                categories={k:[point_to_canvas(*p) for p in v] for k,v in g["categories_mm"].items()},
                category_radius=round(g["category_diameter_mm"]*720/128/2),
                score_box=box_to_canvas(g["score_box_mm"]))

def draw_fiducial_pdf(c,kind,cx,cy,size):
    # Forma y proporciones originales V2.
    half=size/2
    ink=Color(.059,.090,.165)
    c.setFillColor(ink)
    c.setStrokeColor(ink)
    if kind=="solid": c.rect(cx-half,cy-half,size,size,stroke=0,fill=1)
    elif kind=="frame":
        c.rect(cx-half,cy-half,size,size,stroke=0,fill=1)
        c.setFillColor(white)
        inner=size*.40
        c.rect(cx-inner/2,cy-inner/2,inner,inner,stroke=0,fill=1)
        c.setFillColor(ink)
    elif kind=="circle": c.circle(cx,cy,half,stroke=0,fill=1)
    else:
        t=size*.38
        c.rect(cx+half-t,cy-half,t,size,stroke=0,fill=1)
        c.rect(cx-half,cy-half,size,t,stroke=0,fill=1)

def build_sheet_pdf(curso="Publico",settings=None,base_dir=None,paper_size="A5"):
    if paper_size != "A5": raise ValueError("Esta edición usa exclusivamente papel A5.")
    cfg=settings or {}
    g=get_omr_geometry(cfg.get("num_questions",15),cfg.get("num_alternatives",5))
    t=resolve_theme(curso)
    ink=HexColor("#1e3a8a")
    labels=cfg.get("labels") or {}
    brand=cfg.get("branding") or {}
    buf=io.BytesIO()
    c=canvas.Canvas(buf,pagesize=(148*mm,210*mm))
    c.setTitle("Ficha óptica FISMA A5")
    c.setAuthor("OMR FISMA - Alberto Brayan")
    c.setSubject(f"{g['profile']} | {g['num_questions']} preguntas | {g['num_alternatives']} alternativas")

    def text(x,y,value,size=8,color=ink,bold=False,align="left",max_w=None):
        face="Helvetica-Bold" if bold else "Helvetica"
        value=str(value)
        if max_w:
            while size>5.2 and c.stringWidth(value,face,size)>max_w*mm: size-=.2
            while c.stringWidth(value,face,size)>max_w*mm and len(value)>3: value=value[:-4]+"..."
        c.setFillColor(color)
        c.setFont(face,size)
        {"left":c.drawString,"center":c.drawCentredString,"right":c.drawRightString}[align](x*mm,(210-y)*mm,value)
    def box(x,y,w,h,fill=None,stroke=t["border"],r=1.8,lw=.6):
        c.setLineWidth(lw)
        c.setStrokeColor(stroke or white)
        c.setFillColor(fill or white)
        c.roundRect(x*mm,(210-y-h)*mm,w*mm,h*mm,r*mm,stroke=int(stroke is not None),fill=1)
    def line(x1,y1,x2,y2,color=t["border"],lw=.5,dash=None):
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(lw)
        if dash: c.setDash(*dash)
        c.line(x1*mm,(210-y1)*mm,x2*mm,(210-y2)*mm)
        c.restoreState()
    def bubble(x,y,d=5.5,label=None,filled=False):
        c.setStrokeColor(t["primary"])
        c.setLineWidth(.75)
        c.setFillColor(ink if filled else white)
        c.circle(x*mm,(210-y)*mm,d*mm/2,stroke=1,fill=1)
        if label: text(x,y+.78,label,6.5,t["bubble_text"],align="center")

    for corner,(x,y) in g["anchors_mm"].items():
        draw_fiducial_pdf(c,g["anchor_kinds"][corner],x*mm,y*mm,MARKER_SIZE_MM*mm)
    for x,y in SUPPORT_CENTERS_MM.values():
        draw_fiducial_pdf(c,"solid",x*mm,y*mm,SUPPORT_SIZE_MM*mm)
    box(17,18,17,17,t["header_bg"],t["border"],2)
    logo=str(brand.get("logo") or "")
    if logo and not os.path.isabs(logo): logo=os.path.join(base_dir or os.path.dirname(__file__),logo)
    if logo and os.path.isfile(logo):
        from reportlab.lib.utils import ImageReader
        ir=ImageReader(logo)
        iw,ih=ir.getSize()
        scale=min(15/iw,15/ih)
        w,h=iw*scale,ih*scale
        c.drawImage(ir,(25.5-w/2)*mm,(210-26.5-h/2)*mm,w*mm,h*mm,mask="auto")
    else:
        text(25.5,25.5,"FISMA",8.5,t["primary_dark"],True,"center")
        text(25.5,29.2,"FÍSICA",5.3,t["muted"],align="center")
    text(37,22,"FICHA ÓPTICA",14.4,t["primary_dark"],True)
    title=str(brand.get("title") or "I OLIMPIADA ESCOLAR REGIONAL DE FÍSICA 2025").strip()
    # Dos líneas ajustadas al ancho asignado, sin invadir el cuadro Nota.
    words=title.split()
    first=[]
    if " DE FÍSICA" in title.upper():
        split=title.upper().index(" DE FÍSICA")
        first=title[:split].split()
        words=title[split+1:].split()
    else:
        while words and c.stringWidth(" ".join(first+[words[0]]),"Helvetica-Bold",7.1)<72*mm:
            first.append(words.pop(0))
    text(37,28," ".join(first),7.1,ink,True,max_w=72)
    text(37,32.5," ".join(words),8.1,ink,True,max_w=72)
    box(112,18,19,20,None,t["primary"],1.8,.9)
    box(112.3,18.3,18.4,5.2,t["zebra"],None,1.4)
    text(121.5,22.2,"NOTA",7,t["primary_dark"],True,"center")
    line(112,23.8,131,23.8)
    line(17,40,131,40,t["primary"],1.1)
    box(17,43,114,30,t["header_bg"],t["border"],2,.7)
    text(20,48,labels.get("nombre","Apellidos y Nombres").upper(),7.1,t["primary_dark"],True,max_w=108)
    line(20,56.3,128,56.3,dash=(1.1,1.6))
    text(20,62,labels.get("colegio","Institución Educativa").upper(),7.1,t["primary_dark"],True,max_w=108)
    line(20,70.1,128,70.1,dash=(1.1,1.6))
    for x in (17,76): box(x,77,55,17,t["header_bg"],t["border"],1.8,.65)
    text(20,81.8,"NIVEL DE EXAMEN",7,t["primary_dark"],True)
    text(79,81.8,"TIPO DE INSTITUCIÓN",7,t["primary_dark"],True)
    for x,label in ((22,"Nivel VI"),(48,"Nivel VII"),(81,"Público"),(106,"Privado")):
        bubble(x,88.7,5)
        text(x+4,89.5,label,7.2,ink,True)
    text(17,100,"RESPUESTAS",8,t["primary_dark"],True)
    text(131,100,f"{g['num_questions']} preguntas · Una alternativa por pregunta",6.2,t["muted"],align="right")
    for x,start,xs,ys in ((17,1,g["x_left_mm"],g["y_left_mm"]),
                          (76,len(g["y_left_mm"])+1,g["x_right_mm"],g["y_right_mm"])):
        box(x,103,55,5,t["zebra"],None,1)
        text(x+4.4,106.5,"N°",6.2,t["primary_dark"],True,"center")
        text(x+32,106.5,"ALTERNATIVAS",6.2,t["primary_dark"],True,"center")
        for row,ym in enumerate(ys):
            y=210-ym
            if row%2: box(x,y-g["row_h_mm"]*.45,55,g["row_h_mm"]*.9,t["zebra"],None,1)
            text(x+4.4,y+.95,f"{start+row:02d}",8.2,t["primary_dark"],True,"center")
            for xb,letter in zip(xs,g["options"]): bubble(xb,y,5.5,letter)
        line(x,108+5*g["row_h_mm"],x+55,108+5*g["row_h_mm"])
    line(17,180.5,131,180.5,lw=.6)
    text(17,184.8,"LLENADO CON LÁPIZ",5.9,t["primary_dark"],True)
    text(17,189.1,"Correcto",5.7,t["muted"])
    bubble(32.5,188.3,3.3,filled=True)
    text(17,194.1,"Incorrecto",5.7,t["muted"])
    # Ejemplos incorrectos de la referencia: visto, aspa, tachado y punto central.
    for x in (32.5,37.,41.5,46.): bubble(x,193.3,3.3)
    line(31.5,193.2,32.3,194.1,ink,.85)
    line(32.3,194.1,34.3,191.2,ink,.85)
    line(35.9,192.2,38.1,194.4,ink,.85)
    line(35.9,194.4,38.1,192.2,ink,.85)
    c.saveState()
    clip=c.beginPath()
    clip.circle(41.5*mm,(210-193.3)*mm,1.6*mm)
    c.clipPath(clip,stroke=0,fill=0)
    for y in (192.3,193.,193.7,194.4):
        line(39.5,y-.35,43.5,y+.35,ink,.95)
    c.restoreState()
    c.setFillColor(ink)
    c.circle(46.*mm,(210-193.3)*mm,.9*mm,stroke=0,fill=1)
    text(74,184.8,"CONTROL",6.5,t["primary_dark"],True,"center")
    for x,w,label in ((51,21.5,"N° DE ORDEN"),(75.5,21.5,"HORA DE ENTREGA")):
        text(x+w/2,189,label,5.3,t["primary_dark"],True,"center")
        box(x,190.5,w,7,None,t["border"],1.2,.65)
    text(116,184.8,"FIRMA DEL ESTUDIANTE",5.6,t["primary_dark"],True,"center")
    line(101,192,131,192,lw=.6)
    text(101,196.7,"DNI:",6,t["muted"])
    line(106.5,197,131,197,dash=(1,1.5))
    text(74,202,"Usa lápiz 2B. Rellena por completo y no marques las guías negras.",5.4,t["muted"],align="center")
    c.showPage()
    c.save()
    return buf.getvalue(),"ficha_fisma_a5.pdf"
