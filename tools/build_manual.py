"""Genera el HTML sin conexión y el PDF desde una única fuente de contenido.
Uso: python tools/build_manual.py. Las capturas aprobadas están en docs/assets.
"""
from pathlib import Path
import json,html
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Flowable
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
DATA=json.loads((DOCS/'manual_content.json').read_text(encoding='utf-8'))
INK='#12213b'; TEAL='#116d75'; LIGHT='#edf6f6'
esc=lambda text:html.escape(str(text))

def crop_for(section):
    return section.get('crop',[0,0,1,1])

def html_manual():
    toc=''.join(f'<a href="#{s["id"]}"><span>{i:02}</span>{esc(s["title"])}</a>' for i,s in enumerate(DATA['sections'],1))
    parts=[]
    for i,s in enumerate(DATA['sections'],1):
        body=''.join(f'<p>{esc(p)}</p>' for p in s.get('paragraphs',[]))
        steps='<ol>'+''.join(f'<li>{esc(step)}</li>' for step in s.get('steps',[]))+'</ol>' if s.get('steps') else ''
        table=''
        if s.get('table'):
            table='<div class="table-scroll"><table><thead><tr>'+''.join(f'<th>{esc(h)}</th>' for h in s['table']['headers'])+'</tr></thead><tbody>'
            table+=''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in row)+'</tr>' for row in s['table']['rows'])+'</tbody></table></div>'
        code=f'<pre><code>{esc(s["code"])}</code></pre>' if s.get('code') else ''
        figure=''
        if s.get('image'):
            image=DOCS/'assets'/s['image']
            iw,ih=PILImage.open(image).size
            x,y,w,h=crop_for(s)
            figure=f'''<figure><a href="assets/{esc(s['image'])}" target="_blank" rel="noopener" aria-label="Ampliar captura: {esc(s['title'])}">
            <div class="image-window" style="aspect-ratio:{iw*w}/{ih*h}"><img src="assets/{esc(s['image'])}" alt="{esc(s['caption'])}" loading="lazy" style="width:{100/w:.4f}%;left:{-100*x/w:.4f}%;top:{-100*y/h:.4f}%"></div></a>
            <figcaption>{esc(s['caption'])} <span>Selecciona la imagen para ampliarla.</span></figcaption></figure>'''
        note=f'<aside class="note"><strong>Ten en cuenta</strong><p>{esc(s["note"])}</p></aside>' if s.get('note') else ''
        introduction=body+steps if s.get('paragraphs_first') else steps+body
        parts.append(f'<section id="{s["id"]}" class="chapter"><div class="chapter-number">PASO {i:02}</div><h2>{esc(s["title"])}</h2><p class="lead">{esc(s["subtitle"])}</p>{introduction}{table}{code}{figure}{note}</section>')
    css='''
    :root{--ink:#12213b;--muted:#52637a;--teal:#116d75;--line:#dce5eb;--paper:#fff;--wash:#f3f7f9}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 Arial,Helvetica,sans-serif}a{color:var(--teal)}.sidebar{position:fixed;inset:0 auto 0 0;width:270px;padding:28px 22px;background:var(--ink);color:#fff;overflow:auto}.brand{display:flex;gap:12px;align-items:center;margin-bottom:24px}.brand img{width:45px;height:45px;border-radius:50%;background:white;object-fit:contain}.brand strong{font-size:20px;display:block}.brand small{color:#b8cbd9}.sidebar nav a{display:flex;gap:12px;color:#dbe7ed;text-decoration:none;font-size:13px;line-height:1.45;padding:10px 4px;border-bottom:1px solid #293954}.sidebar nav a:hover,.sidebar nav a:focus-visible{color:white;background:#1e3551}.sidebar nav span{color:#75c4c4;font-variant-numeric:tabular-nums}.sidebar .edition{font-size:12px;color:#b8cbd9;margin-top:24px}main{margin-left:270px;padding:44px clamp(24px,5vw,80px);max-width:1320px}.hero{border-bottom:2px solid var(--teal);padding-bottom:32px;margin-bottom:32px}.eyebrow,.chapter-number{font-size:12px;letter-spacing:.1em;font-weight:bold;color:var(--teal)}h1{font-size:clamp(34px,4vw,50px);line-height:1.1;margin:14px 0 18px;letter-spacing:-.02em}.hero p{max-width:650px;font-size:18px;color:var(--muted)}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0 16px}.button,button{font:inherit;font-size:14px;font-weight:bold;padding:11px 18px;border-radius:5px;border:1px solid var(--teal);cursor:pointer;text-decoration:none;background:var(--teal);color:white}.button.secondary{background:white;color:var(--teal)}.facts{display:flex;gap:12px;flex-wrap:wrap;font-size:13px;color:var(--muted)}.facts span{padding-right:14px;border-right:1px solid var(--line)}.chapter{background:white;border:1px solid var(--line);padding:32px;margin:0 0 28px;border-radius:8px}h2{font-size:27px;line-height:1.22;margin:9px 0 12px}.lead{color:var(--teal);font-size:17px;margin-top:0}p{margin:14px 0}ol{padding-left:24px}li{padding-left:6px;margin-bottom:12px}li::marker{font-weight:bold;color:var(--teal)}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin:22px 0}th{text-align:left;background:var(--ink);color:white}th,td{padding:11px 12px;vertical-align:top;border:1px solid var(--line)}tbody tr:nth-child(even){background:#f4f7fa}pre{background:#14223a;color:#e8f2f6;padding:22px;overflow:auto;border-radius:5px;font:14px/1.6 Consolas,monospace}.note{border-left:4px solid var(--teal);background:#edf6f6;padding:16px 20px;margin-top:24px}.note strong{font-size:13px;color:var(--teal)}.note p{margin:6px 0;font-size:14px}.image-window{position:relative;overflow:hidden;background:#0c1424;border-radius:5px;border:1px solid var(--line);max-height:650px}.image-window img{position:absolute;height:auto;max-width:none;display:block}figure{margin:24px 0}figcaption{font-size:12px;line-height:1.5;color:var(--muted);margin-top:9px}figcaption span{display:block;color:var(--teal)}footer{font-size:12px;color:var(--muted);padding:10px 0 26px;border-top:1px solid var(--line)}:focus-visible{outline:3px solid #de9e2b;outline-offset:3px}@media(max-width:950px){.sidebar{position:static;width:auto}.sidebar nav{display:grid;grid-template-columns:1fr 1fr}.sidebar .edition{display:none}main{margin-left:0;padding:28px 18px}.chapter{padding:24px}h2{font-size:24px}}@media(max-width:520px){.sidebar nav{grid-template-columns:1fr}body{font-size:15px}.chapter{padding:19px}}@media print{body{background:white;font-size:11pt}.sidebar,.actions{display:none}main{margin:0;padding:0;max-width:none}.hero{break-after:page}.chapter{border:0;padding:0;break-before:page;margin:0}a{color:inherit;text-decoration:none}figure{break-inside:avoid}.image-window{max-height:none}footer{margin-top:20px}h2{font-size:20pt}.note{break-inside:avoid}}
    '''
    document=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Manual de uso web de Fisma OMR: claves, fichas A5, lotes, observaciones y resultados."><title>Fisma OMR | Manual de uso web</title><style>{css}</style></head><body>
    <aside class="sidebar"><div class="brand"><img src="assets/logo-fisma.png" alt="Emblema FISMA"><div><strong>Fisma OMR</strong><small>Manual de uso web</small></div></div><nav aria-label="Contenido del manual">{toc}</nav><p class="edition">Edición {DATA['edition']}<br>{DATA['date']}<br>Capturas con datos de demostración.</p></aside>
    <main><header class="hero"><div class="eyebrow">GUÍA DEL OPERADOR · EDICIÓN {DATA['edition']}</div><h1>{DATA['title']}</h1><p>{esc(DATA['intro'])}</p><div class="actions"><a class="button" href="Manual_Fisma_OMR_Web.pdf" download>Descargar manual PDF</a><button class="button secondary" onclick="window.print()">Imprimir esta guía</button></div><div class="facts"><span>A5 · 15 preguntas · 5 alternativas</span><span>Niveles VI / VII</span><span>Público / Privado</span></div></header>{''.join(parts)}<footer>© 2026 Alberto Brayan · Fisma OMR · Todos los derechos reservados.<br>Los componentes de terceros conservan sus licencias. Los ejemplos de este manual no son claves ni resultados oficiales.</footer></main></body></html>'''
    (DOCS/'index.html').write_text(document,encoding='utf-8')

class CropImage(Flowable):
    def __init__(self,path,crop,width,max_height):
        Flowable.__init__(self)
        self.path=str(path); self.crop=crop
        iw,ih=PILImage.open(path).size
        self.iw,self.ih=iw,ih
        _,_,cw,ch=crop
        scale=min(width/(iw*cw),max_height/(ih*ch))
        self.width=iw*cw*scale; self.height=ih*ch*scale; self.scale=scale
        self.hAlign='CENTER'
    def draw(self):
        c=self.canv; x,y,cw,ch=self.crop
        c.saveState(); path=c.beginPath(); path.rect(0,0,self.width,self.height); c.clipPath(path,stroke=0)
        c.drawImage(self.path,-self.iw*x*self.scale,
            self.height-self.ih*(1-y)*self.scale,width=self.iw*self.scale,height=self.ih*self.scale)
        c.restoreState()

class Anchor(Flowable):
    width=height=0
    def __init__(self,s): Flowable.__init__(self); self.s=s
    def draw(self):
        self.canv.bookmarkPage('sec-'+self.s['id'])
        self.canv.addOutlineEntry(self.s['title'],'sec-'+self.s['id'],0)

def pdf_manual():
    W,H=A4; content_w=174*mm; frame_h=254*mm
    pstyle=ParagraphStyle('body',fontName='Helvetica',fontSize=10.1,leading=14.2,textColor=colors.HexColor(INK),spaceAfter=7)
    stepstyle=ParagraphStyle('step',parent=pstyle,leftIndent=15,firstLineIndent=-15,spaceAfter=7)
    title=ParagraphStyle('title',parent=pstyle,fontName='Helvetica-Bold',fontSize=23,leading=26,spaceAfter=9)
    subtitle=ParagraphStyle('sub',parent=pstyle,fontSize=11,leading=15,textColor=colors.HexColor(TEAL),spaceAfter=14)
    caption=ParagraphStyle('caption',parent=pstyle,fontSize=8.2,leading=11,textColor=colors.HexColor('#53647a'),spaceBefore=6,spaceAfter=7)
    note_style=ParagraphStyle('note',parent=pstyle,fontSize=9.2,leading=13,spaceAfter=0)
    table_style=ParagraphStyle('cell',parent=pstyle,fontSize=9.0,leading=12,spaceAfter=0)
    table_header=ParagraphStyle('head',parent=table_style,fontName='Helvetica-Bold',textColor=colors.white)
    def para(value,style=pstyle): return Paragraph(esc(value),style)
    def note(text):
        table=Table([[Paragraph('<b>Ten en cuenta</b><br/>'+esc(text),note_style)]],colWidths=[content_w])
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(LIGHT)),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#c5dfe0')),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        return table
    def height_of(flows): return sum(f.wrap(content_w,frame_h)[1]+f.getSpaceBefore()+f.getSpaceAfter() for f in flows)
    def draw_page(c,doc):
        c.saveState()
        if doc.page==1:
            c.setFillColor(colors.HexColor(INK));c.rect(0,0,W,H,stroke=0,fill=1)
            c.setFillColor(colors.HexColor('#55c6c6'));c.rect(20*mm,249*mm,20*mm,2*mm,stroke=0,fill=1)
            c.setFillColor(colors.white);c.setFont('Helvetica-Bold',35);c.drawString(20*mm,235*mm,'Fisma OMR')
            c.setFont('Helvetica',24);c.drawString(20*mm,220*mm,'Manual de uso web')
            c.setFillColor(colors.HexColor('#b9d4df'));c.setFont('Helvetica',11)
            c.drawString(20*mm,208*mm,'FICHA A5  /  15 PREGUNTAS  /  5 ALTERNATIVAS')
            cover_style=ParagraphStyle('cover',fontName='Helvetica',fontSize=13,leading=19,textColor=colors.white)
            p=Paragraph(esc(DATA['intro']),cover_style); _,ph=p.wrap(158*mm,100*mm);p.drawOn(c,20*mm,192*mm-ph)
            c.setFont('Helvetica-Bold',11);c.setFillColor(colors.HexColor('#78d7d4'));c.drawString(20*mm,150*mm,'CONTENIDO')
            y=140*mm
            for i,s in enumerate(DATA['sections'],1):
                c.setFont('Helvetica-Bold',9.5);c.setFillColor(colors.HexColor('#78d7d4'));c.drawString(20*mm,y,f'{i:02}')
                c.setFont('Helvetica',10.2);c.setFillColor(colors.white);c.drawString(30*mm,y,s['title'])
                c.setFont('Helvetica',9);c.drawRightString(188*mm,y,str(i+1))
                c.linkRect('', 'sec-'+s['id'],(20*mm,y-3,188*mm,y+11),relative=0,thickness=0)
                y-=8*mm
            c.setStrokeColor(colors.HexColor('#38516b'));c.line(20*mm,43*mm,188*mm,43*mm)
            c.setFont('Helvetica',9);c.setFillColor(colors.HexColor('#b9d4df'));c.drawString(20*mm,34*mm,f"Edición {DATA['edition']} · {DATA['date']}")
            c.drawString(20*mm,27*mm,'Capturas y ejemplos con datos de demostración.')
            c.setFont('Helvetica',7.5);c.drawString(20*mm,17*mm,'© 2026 Alberto Brayan · Todos los derechos reservados.')
            logo=DOCS/'assets/logo-fisma.png'
            if logo.exists():
                c.setFillColor(colors.white);c.circle(177*mm,255*mm,14*mm,stroke=0,fill=1)
                c.drawImage(str(logo),164*mm,242*mm,width=26*mm,height=26*mm,preserveAspectRatio=True,mask='auto')
        else:
            c.setFont('Helvetica-Bold',8);c.setFillColor(colors.HexColor(TEAL));c.drawString(18*mm,283*mm,'FISMA OMR')
            c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#53647a'));c.drawRightString(192*mm,283*mm,'MANUAL DE USO WEB · A5.6')
            c.setStrokeColor(colors.HexColor('#dbe5eb'));c.line(18*mm,279*mm,192*mm,279*mm)
            c.line(18*mm,16*mm,192*mm,16*mm)
            c.setFont('Helvetica',7.2);c.drawString(18*mm,10*mm,'© 2026 Alberto Brayan · Todos los derechos reservados')
            c.drawRightString(192*mm,10*mm,f'{doc.page} / {len(DATA["sections"])+1}')
        c.restoreState()
    story=[Spacer(1,1),PageBreak()]
    for i,s in enumerate(DATA['sections'],1):
        if i>1: story.append(PageBreak())
        flows=[Anchor(s),Paragraph(f'{i:02}. {esc(s["title"])}',title),para(s['subtitle'],subtitle)]
        paragraphs=[para(p) for p in s.get('paragraphs',[])]
        steps=[Paragraph(f'<b>{j}.</b> {esc(step)}',stepstyle) for j,step in enumerate(s.get('steps',[]),1)]
        flows += paragraphs+steps if s.get('paragraphs_first') else steps+paragraphs
        if s.get('table'):
            headings=s['table']['headers']; count=len(headings)
            widths=[content_w/count]*count
            if count==2: widths=[content_w*.31,content_w*.69]
            values=[[para(h,table_header) for h in headings]]+[[para(v,table_style) for v in row] for row in s['table']['rows']]
            t=Table(values,colWidths=widths,hAlign='LEFT',repeatRows=1)
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(INK)),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f8')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d7e2e8')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            flows.extend([Spacer(1,5),t,Spacer(1,9)])
        if s.get('code'):
            code_style=ParagraphStyle('code',fontName='Courier',fontSize=9,leading=12,textColor=colors.HexColor(INK))
            code=Paragraph(esc(s['code']).replace(' ','&#160;').replace('\n','<br/>'),code_style)
            flows.extend([code,Spacer(1,9)])
        tail=[Spacer(1,7),note(s['note'])] if s.get('note') else []
        if s.get('image'):
            caption_flow=para(s['caption'],caption)
            free=frame_h-height_of(flows+tail+[caption_flow])-22
            if free<25*mm: raise RuntimeError(f'Sección sin espacio para imagen: {s["id"]}, {free:.1f}pt')
            figure=CropImage(DOCS/'assets'/s['image'],crop_for(s),content_w,min(83*mm,free))
            flows += [Spacer(1,5),figure,caption_flow]
        flows+=tail
        if height_of(flows)>frame_h-8:
            raise RuntimeError(f'Sección demasiado alta: {s["id"]}')
        story+=flows
    target=DOCS/'Manual_Fisma_OMR_Web.pdf'
    document=SimpleDocTemplate(str(target),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=23*mm,bottomMargin=20*mm,
        title='Fisma OMR - Manual de uso web',author='Alberto Brayan',subject='Guía del operador - A5.6',pageCompression=1)
    document.build(story,onFirstPage=draw_page,onLaterPages=draw_page)

if __name__=='__main__':
    html_manual();pdf_manual()
    print('Manual HTML y PDF generados en docs/.')
