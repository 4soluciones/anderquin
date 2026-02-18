import decimal
import reportlab
from django.http import HttpResponse, response
from reportlab.lib.colors import black, white, gray, red, green, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, tables, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import Table, Flowable, Image
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.rl_settings import defaultPageSize
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color, black, blue, red, pink
from anderquin import settings
from .models import Guide, GuideMotive, GuideDetail, Picking, PickingDetail, Transfer, TransferDetail
from apps.sales.number_to_letters import numero_a_moneda
import io
import os
import datetime

from ..sales.format_dates import utc_to_local
from ..sales.models import ProductDetail, ClientAddress
from ..sales.views import calculate_minimum_unit

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Title1', alignment=TA_JUSTIFY, leading=8, fontName='Helvetica', fontSize=12))
styles.add(ParagraphStyle(name='Left-text', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Left_Square', alignment=TA_LEFT, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=10))
styles.add(
    ParagraphStyle(name='Justify_Newgot_title', alignment=TA_JUSTIFY, leading=14, fontName='Newgot', fontSize=14))
styles.add(
    ParagraphStyle(name='Center_Newgot_title', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=15))
styles.add(
    ParagraphStyle(name='Center_Newgots', alignment=TA_CENTER, leading=13, fontName='Newgot', fontSize=13))
styles.add(
    ParagraphStyle(name='Center_Newgots_invoice', alignment=TA_CENTER, leading=13, fontName='Newgot', fontSize=13,
                   textColor=white))
styles.add(
    ParagraphStyle(name='Left_Newgots', alignment=TA_LEFT, leading=14, fontName='Newgot', fontSize=13))
styles.add(ParagraphStyle(name='Justify_Newgot', alignment=TA_JUSTIFY, leading=10, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Center_Newgot', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=11))
styles.add(ParagraphStyle(name='CenterNewgotBold', alignment=TA_CENTER, leading=9, fontName='Newgot', fontSize=9))
styles.add(
    ParagraphStyle(name='CenterNewgotBold_Footer', alignment=TA_CENTER, leading=9, fontName='Newgot', fontSize=6))
styles.add(ParagraphStyle(name='LeftNewgotBold', alignment=TA_LEFT, leading=9, fontName='Newgot', fontSize=9))
styles.add(ParagraphStyle(name='Right_Newgot', alignment=TA_RIGHT, leading=12, fontName='Newgot', fontSize=12))
styles.add(
    ParagraphStyle(name='Justify_Lucida', alignment=TA_JUSTIFY, leading=11, fontName='Lucida-Console', fontSize=11))
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, leading=14, fontName='Square', fontSize=12))
styles.add(ParagraphStyle(name='Justify-Dotcirful', alignment=TA_JUSTIFY, leading=11, fontName='Dotcirful-Regular',
                          fontSize=11))
styles.add(
    ParagraphStyle(name='Justify-Dotcirful-table', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                   fontSize=7))
styles.add(ParagraphStyle(name='Justify_Bold', alignment=TA_JUSTIFY, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='CenterBold', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(
    ParagraphStyle(name='Justify_Square_Bold', alignment=TA_JUSTIFY, leading=5, fontName='Square-Bold', fontSize=10))
styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Center_a4', alignment=TA_CENTER, leading=12, fontName='Square', fontSize=12))
styles.add(ParagraphStyle(name='Left_square_title', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=6))
styles.add(ParagraphStyle(name='Justify_a4', alignment=TA_JUSTIFY, leading=12, fontName='Square', fontSize=12))
styles.add(
    ParagraphStyle(name='Center-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular', fontSize=10))
styles.add(ParagraphStyle(name='CenterNewgotBoldInvoiceNumber', alignment=TA_CENTER, leading=11, fontName='Newgot',
                          fontSize=11))
styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=12))
styles.add(ParagraphStyle(name='CenterTitle', alignment=TA_CENTER, leading=14, fontName='Square-Bold', fontSize=14))
styles.add(ParagraphStyle(name='CenterTitle-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=11))
styles.add(ParagraphStyle(name='Center2', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=8))
styles.add(ParagraphStyle(name='Center3', alignment=TA_JUSTIFY, leading=8, fontName='Ticketing', fontSize=7))
styles.add(ParagraphStyle(name='narrow_justify', alignment=TA_JUSTIFY, leading=11, fontName='Narrow', fontSize=10))
styles.add(
    ParagraphStyle(name='narrow_justify_observation', alignment=TA_JUSTIFY, leading=9, fontName='Narrow', fontSize=8))
styles.add(ParagraphStyle(name='narrow_center', alignment=TA_CENTER, leading=10, fontName='Narrow', fontSize=10))
styles.add(ParagraphStyle(name='narrow_center_pie', alignment=TA_CENTER, leading=8, fontName='Narrow', fontSize=8))
styles.add(ParagraphStyle(name='narrow_left', alignment=TA_LEFT, leading=12, fontName='Narrow', fontSize=10))
styles.add(ParagraphStyle(name='narrow_a_justify', alignment=TA_JUSTIFY, leading=10, fontName='Narrow-a', fontSize=9))
styles.add(ParagraphStyle(name='narrow_a_left', alignment=TA_LEFT, leading=10, fontName='Narrow-a', fontSize=7))
styles.add(ParagraphStyle(name='narrow_a_center_9', alignment=TA_CENTER, leading=10, fontName='Narrow-a', fontSize=7))
styles.add(ParagraphStyle(name='narrow_a_right_9', alignment=TA_RIGHT, leading=10, fontName='Narrow-a', fontSize=7))
styles.add(ParagraphStyle(name='narrow_a_right_8', alignment=TA_RIGHT, leading=10, fontName='Narrow-a', fontSize=8))
styles.add(ParagraphStyle(name='narrow_a_left_8', alignment=TA_LEFT, leading=10, fontName='Narrow-a', fontSize=8))
styles.add(ParagraphStyle(name='narrow_a_left_foot', alignment=TA_LEFT, leading=10, fontName='Narrow-a', fontSize=6))
styles.add(ParagraphStyle(name='narrow_a_center', alignment=TA_CENTER, leading=10, fontName='Narrow-a', fontSize=9))
styles.add(
    ParagraphStyle(name='narrow_b_justify', alignment=TA_JUSTIFY, leading=11, fontName='Narrow-b',
                   fontSize=10))
styles.add(
    ParagraphStyle(name='narrow_b_tittle_justify', alignment=TA_JUSTIFY, leading=12, fontName='Narrow-b', fontSize=12))
styles.add(
    ParagraphStyle(name='narrow_b_normal_justify', alignment=TA_JUSTIFY, leading=10, fontName='Narrow-b', fontSize=8))
styles.add(ParagraphStyle(name='narrow_b_left', alignment=TA_LEFT, leading=9, fontName='Narrow-b', fontSize=8))
styles.add(ParagraphStyle(name='narrow_b_center', alignment=TA_CENTER, leading=9, fontName='Narrow-b', fontSize=10))
styles.add(ParagraphStyle(name='narrow_c_justify', alignment=TA_JUSTIFY, leading=10, fontName='Narrow-c', fontSize=10))
style = styles["Normal"]
styles.add(ParagraphStyle(name='CenterNewgotBoldGuideNumber', alignment=TA_CENTER, leading=11, fontName='Newgot',
                          fontSize=11))
styles.add(ParagraphStyle(name='CenterNewgotTitle', alignment=TA_CENTER, leading=14, fontName='Newgot',
                          fontSize=14))
styles.add(ParagraphStyle(name='resort_left', alignment=TA_LEFT, leading=11, fontName='All-Star-Resort',
                          fontSize=16, textColor=black))

style = styles["Normal"]

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
pdfmetrics.registerFont(TTFont('Narrow', 'Arial Narrow.ttf'))
pdfmetrics.registerFont(TTFont('Narrow-a', 'ARIALN.TTF'))
pdfmetrics.registerFont(TTFont('Narrow-b', 'ARIALNB.TTF'))
pdfmetrics.registerFont(TTFont('Narrow-c', 'Arialnbi.ttf'))
# pdfmetrics.registerFont(TTFont('Narrow-d', 'ARIALNI.TTF'))
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))
pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))
pdfmetrics.registerFont(TTFont('Dotcirful-Regular', 'DotcirfulRegular.otf'))
pdfmetrics.registerFont(TTFont('Ticketing', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucida-console.ttf'))
pdfmetrics.registerFont(TTFont('Square-Dot', 'square_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Dot', 'serif_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Enhanced-Dot-Digital', 'enhanced-dot-digital-7.regular.ttf'))
pdfmetrics.registerFont(TTFont('Merchant-Copy-Wide', 'MerchantCopyWide.ttf'))
pdfmetrics.registerFont(TTFont('Dot-Digital', 'dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Raleway-Dots-Regular', 'RalewayDotsRegular.ttf'))
pdfmetrics.registerFont(TTFont('Ordre-Depart', 'Ordre-de-Depart.ttf'))
pdfmetrics.registerFont(TTFont('Nationfd', 'Nationfd.ttf'))
pdfmetrics.registerFont(TTFont('Kg-Primary-Dots', 'KgPrimaryDots-Pl0E.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line', 'Dotline-LA7g.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line-Light', 'DotlineLight-XXeo.ttf'))
pdfmetrics.registerFont(TTFont('Jd-Lcd-Rounded', 'JdLcdRoundedRegular-vXwE.ttf'))
pdfmetrics.registerFont(TTFont('All-Star-Resort', 'All Star Resort.ttf'))

logo = "static/assets/avatar/logo-anderquin-original.png"


def guide_print(self, pk=None):
    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="operating_lease_contract.pdf"'

    buff = io.BytesIO()

    xmax = 595
    ymax = 842

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            )
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
                              leading=13, fontName='Newgot', fontSize=12))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER,
                              leading=13, fontName='Square', fontSize=11))

    # pdfmetrics.registerFont(TTFont('Square', os.path.dirname(os.path.abspath(__file__)) + '/static/fonts/sqr721bc.ttf'))
    # products = []
    # styles = getSampleStyleSheet()
    header = Paragraph("Listado de Productos", styles['Center'])

    Story = []

    Story.append(header)
    Story.append(Spacer(1, 13))
    ptext = 'Conste el presente contrato de arrendamiento operativo, que celebran de una parte la \
                empresa SERVICIOS GENERALES TURISMO AREQUIPA S.A.C., representado por su Gerente \
                General don GUSTAVO GUILLERMO MUÑOZ TACUSI, identificado con DNI N° 29326621, con \
                domicilio en la Av. Tacna y Arica 207, distrito Cercado, Provincia de Arequipa, a quien en lo \
                sucesivo se denominará <b>LA EMPRESA</b> y de otra parte don %s \
                identificado con DNI N° %s con domicilio en %s a quien en lo sucesivo se denominará \
                <b>EL PROPIETARIO AFILIADO</b>; en los términos contenidos en las siguientes cláusulas:'

    Story.append(Paragraph(ptext, styles["Justify"]))

    # products.append(header)
    # headings = ('Id', 'Descrición', 'Activo', 'Creación')
    # if not pk:
    #     all_products = [(p.id, p.name, p.is_enabled, p.code)
    #                     for p in Product.objects.all().order_by('pk')]
    # else:
    #     all_products = [(p.id, p.name, p.is_enabled, p.code)
    #                     for p in Product.objects.filter(id=pk)]
    # t = Table([headings] + all_products)
    # t.setStyle(TableStyle(
    #     [
    #         ('GRID', (0, 0), (3, -1), 1, colors.dodgerblue),
    #         ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
    #         ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue)
    #     ]
    # ))
    #
    # Story.append(t)

    doc.build(Story, onLaterPages=operating_lease_contract_template)
    response.write(buff.getvalue())
    buff.close()
    return response


def operating_lease_contract_template(canvas, doc):
    xmax = 595
    ymax = 842

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    if doc.page == 1:
        # Save the current settings
        canvas.saveState()

        canvas.setFillColor(black)
        # canvas.setFont('Helvetica-Bold', 10)
        canvas.setDash(1, 1)
        canvas.line(ml - ms + 155, 100, ml - ms + 285, 100)
        canvas.line(ml - ms + 335, 100, ml - ms + 485, 100)

        canvas.drawString(ml - ms + 185, 85, 'LA EMPRESA')
        canvas.drawString(ml - ms + 343, 85, 'EL PROPIETARIO AFILIADO')

        # Restore setting to before function call
        canvas.restoreState()
        # translate then scale
        canvas.translate(2.4 * inch, 1.5 * inch)
        canvas.scale(0.3, 0.5)
        canvas.drawString(0, 2.7 * inch, "Translate then scale")


def myFirstPage(request):
    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="owners_and_vehicles_update.pdf"'
    xmax = 21 * cm
    ymax = 29.7 * cm

    ml = 3 * cm
    mr = 3 * cm
    ms = 2.5 * cm
    mi = 2.5 * cm

    width_page = xmax - 2 * mr

    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)

    canvas.setLineWidth(.3)

    canvas.setFont('Times-Bold', 12)
    canvas.drawString(ml + 30, 795, 'FICHA DE ACTUALIZACION DEL PROPIETARIO  Y VEHÍCULO')

    canvas.setFillColor(white)
    canvas.rect(ml, 740, 50, 36, stroke=1, fill=1)
    canvas.rect(ml + 50, 740, 35, 36, stroke=1, fill=1)
    canvas.rect(ml + 50 + 35, 740, 35, 36, stroke=1, fill=1)
    canvas.rect(ml + 50 + 35 + 35, 740, 35, 36, stroke=1, fill=1)
    canvas.line(ml + 50, 740 + 18, ml + 50 + 35 + 35 + 35, 740 + 18)

    canvas.rect(ml + 200, 740, 50, 36, stroke=1, fill=1)

    canvas.rect(ml + 275 - 15, 740, 46, 36, stroke=1, fill=1)
    canvas.rect(ml + 275 - 15 + 46, 740, 44, 36, stroke=1, fill=1)
    canvas.rect(ml + 275 - 15 + 46 + 44, 740, 75, 36, stroke=1, fill=1)
    canvas.line(ml + 275 - 15, 740 + 18, ml + 275 + 40 + 40 + 70, 740 + 18)
    canvas.line(ml + 275 + 40 + 40 + 35, 740, ml + 275 + 40 + 40 + 35, 740 + 18)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 4, 740 + 9 + 4, "FECHA")
    canvas.drawString(ml + 50 + 4, 740 + 18 + 4, "DÍA")
    canvas.drawString(ml + 50 + 35 + 4, 740 + 18 + 4, "MES")
    canvas.drawString(ml + 50 + 35 + 35 + 4, 740 + 18 + 4, "AÑO")

    canvas.drawString(ml + 50 + 35 + 35 + 4, 740 + 4, "2017")

    canvas.drawString(ml + 50 * 2 + 35 * 2 + 4, 740 + 9 + 4, "Móvil")

    canvas.setFont('Helvetica', 6)
    canvas.drawString(ml + 275 - 15 + 2, 740 + 18 + 4, "PROPIETARIO")
    canvas.drawString(ml + 275 - 15 + 46 + 2, 740 + 18 + 4, "CONDUCTOR")
    canvas.drawString(ml + 275 - 15 + 46 + 44 + 2, 740 + 18 + 4, "EQUIPO COMUNICACIÓN")

    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 275 - 15 + 46 + 66 + 2, 740 + 4, "SI")
    canvas.drawString(ml + 275 - 15 + 46 + 66 + 22 + 2, 740 + 4, "NO")

    canvas.setFillColor(black)
    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml - 0, 715, 'I.- DATOS DE LA PERSONA JURIDICA')

    # canvas.setFillColor(white)
    # canvas.rect(ml - 0, 710, width_page, 10, stroke=1, fill=1)

    canvas.setFillColor(white)
    canvas.rect(ml, 690, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 690, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 690, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 675, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 675, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 675, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 645, 42, 30, stroke=1, fill=1)
    canvas.rect(ml + 42, 645, 100, 30, stroke=1, fill=1)
    canvas.rect(ml + 142, 645, 142, 30, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 645, 80, 30, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142 + 80, 645, 61, 30, stroke=1, fill=1)
    canvas.line(ml + 42, 645 + 15, ml + 142 + 142 + 80 + 61, 645 + 15)

    canvas.rect(ml, 630, 42, 15, stroke=1, fill=1)
    canvas.rect(ml + 42, 630, 425 - 42, 15, stroke=1, fill=1)

    canvas.rect(ml, 570, 42, 60, stroke=1, fill=1)
    canvas.rect(ml + 42, 570, 42, 60, stroke=1, fill=1)
    canvas.rect(ml + 42 + 42, 570, 425 - 42 - 42, 60, stroke=1, fill=1)

    canvas.line(ml + 42 + 42, 570 + 15, ml + 42 + 42 + 425 - 42 - 42, 570 + 15)
    canvas.line(ml + 42 + 42, 570 + 30, ml + 42 + 42 + 425 - 42 - 42, 570 + 30)
    canvas.line(ml + 42 + 42, 570 + 45, ml + 42 + 42 + 425 - 42 - 42, 570 + 45)

    canvas.line(ml + 42 + 42 + (425 - 42 - 42) / 3, 570,
                ml + 42 + 42 + (425 - 42 - 42) / 3, 570 + 60)
    canvas.line(ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2, 570,
                ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2, 570 + 30)
    canvas.line(ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6, 570 + 30,
                ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6, 570 + 60)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 4, 690 + 4, "Ap. Paterno")
    canvas.drawString(ml + 142 + 4, 690 + 4, "Ap. Materno")
    canvas.drawString(ml + 142 * 2 + 4, 690 + 4, "Nombres")

    canvas.drawString(ml + 4, 645 + 15 + 4, "DOC")
    canvas.drawString(ml + 4, 645 + 4, "Ident.")

    canvas.drawString(ml + 42 + 4, 645 + 15 + 4, "DNI/L.E.")
    canvas.drawString(ml + 142 + 4, 645 + 15 + 4, "Lic.Cond./Cat.")
    canvas.drawString(ml + 142 * 2 + 4, 645 + 15 + 4, "Fecha Nac.")
    canvas.drawString(ml + 142 * 2 + 80 + 4, 645 + 15 + 4, "Est. Civil")
    canvas.drawString(ml + 4, 630 + 4, "E-mail")

    canvas.drawString(ml + 42 * 2 + 4, 570 + 45 + 4, "Av. Calle, Jr. Pje.")
    canvas.drawString(ml + 42 + 42 + (425 - 42 - 42) / 3 + 4,
                      570 + 45 + 4, "Mz. N°, Zona, Int., Of.")
    canvas.drawString(ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6 + 4, 570 + 45 + 4, "Tf.")

    canvas.drawString(ml + 42 * 2 + 4, 570 + 15 + 4, "Urb.")
    canvas.drawString(ml + 42 + 42 + (425 - 42 - 42) / 3 + 4, 570 + 15 + 4, "Distr.")
    canvas.drawString(ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2 + 4, 570 + 15 + 4, "Provincia")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 545, 'II.- DATOS REGISTRALES')

    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(ml, 528,
                      "Si usted cuenta con alguno de los siguientes documentos, complete los siguientes recuadros:")
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.drawString(ml, 515, "Marque con una (X) en el recuadro seleccionado")

    canvas.setFillColor(colors.lightgrey)

    canvas.line(ml + 105 + 52.5, 360, ml + 105 + 52.5, 360 + 150)

    canvas.rect(ml, 480, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 480 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 450, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 450 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 420, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 420 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 390, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 390 + 15, 105 * 2 + 110, 15, stroke=1, fill=1)
    canvas.rect(ml, 360, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 360 + 15, 105 * 2 + 110, 15, stroke=1, fill=1)

    canvas.line(ml + 105 * 2, 360, ml + 105 * 2, 360 + 150)
    canvas.line(ml + 105 * 3, 360, ml + 105 * 3, 360 + 150)
    canvas.line(ml + 105 * 3 + 110 - 110 / 3, 360, ml + 105 * 3 + 110 - 110 / 3, 360 + 60)
    canvas.line(ml + 105 * 3 + 110, 360, ml + 105 * 3 + 110, 360 + 60)

    canvas.line(ml + 105, 360, ml + 105 * 3 + 110, 360)

    canvas.setFillColor(black)

    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(ml + 0 + 4, 480 + 7.5 + 4, "SETARE")
    canvas.drawString(ml + 0 + 4, 450 + 15 + 4, "PERMISO")
    canvas.drawString(ml + 0 + 4, 450 + 0 + 4, "PROVISIONAL")
    canvas.drawString(ml + 0 + 4, 420 + 0 + 4, "AFOCAT")
    canvas.drawString(ml + 0 + 4, 390 + 0 + 4, "SOAT")
    canvas.drawString(ml + 0 + 4, 360 + 0 + 4, "REVISION TECNICA")

    canvas.setFont('Helvetica', 8)
    canvas.drawString(ml + 105 * 1 + 30 + 4, 480 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 480 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 480 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 480 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 480 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 480 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 450 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 450 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 450 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 450 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 450 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 450 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 420 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 420 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 420 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 420 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 420 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 420 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 390 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 390 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 3 + 4, 390 + 15 + 4, "PARTICULAR")
    canvas.drawString(ml + 105 * 3 + 80 + 4, 390 + 15 + 4, "TAXI")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 390 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 390 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 390 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 390 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 360 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 360 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 3 + 4, 360 + 15 + 4, "PARTICULAR")
    canvas.drawString(ml + 105 * 3 + 80 + 4, 360 + 15 + 4, "TAXI")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 360 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 360 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 360 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 360 + 0 + 4, "/")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 340, 'III.- DATOS DEL VEHÍCULO')

    canvas.setFillColor(white)
    canvas.rect(ml, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 2, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 3, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 4, 310, 85, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 2, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 3, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 4, 310 - 15, 85, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15 * 2, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 310 - 15 * 2, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 * 2, 310 - 15 * 2, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15 * 3, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 310 - 15 * 3, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 * 2, 310 - 15 * 3, 141, 15, stroke=1, fill=1)

    canvas.setFillColor(black)
    canvas.drawString(ml + 4, 310 + 0 + 4, "Placa")
    canvas.drawString(ml + 85 + 4, 310 + 0 + 4, "Marca")
    canvas.drawString(ml + 85 * 2 + 4, 310 + 0 + 4, "Modelo")
    canvas.drawString(ml + 85 * 3 + 4, 310 + 0 + 4, "Año")
    canvas.drawString(ml + 85 * 4 + 4, 310 + 0 + 4, "Color")

    canvas.drawString(ml + 142 * 0 + 4, 310 - 15 * 2 + 0 + 4, "N° Serie")
    canvas.drawString(ml + 142 * 1 + 4, 310 - 15 * 2 + 0 + 4, "Motor")
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(ml + 142 * 2 + 4, 310 - 15 * 2 + 0 + 4, "CARACTERISTICAS ESPECIALES")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 250, 'IV.- DOCUMENTOS ADJUNTOS')

    canvas.setFillColor(white)
    canvas.rect(ml, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15 * 2, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15 * 2, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15 * 2, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15 * 3, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15 * 3, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15 * 3, 122, 15, stroke=1, fill=1)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 9)
    canvas.drawString(ml + 20 + 4, 220 - 15 * 0 + 4, "Fotocopia DNI (Propietario).")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 0 + 4, "Fotocopia AFOCAT.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 0 + 4, "Copia recibo agua.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 1 + 4, "Fotocopia DNI (Cónyuge).")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 1 + 4, "Fotocopia R. TECNICA.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 1 + 4, "Copia recibo luz.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 2 + 4, "Fotocopia Tarjeta Propiedad.")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 2 + 4, "Fotocopia SETARE.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 2 + 4, "Copia recibo teléfono o cable.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 3 + 4, "Fotocopia SOAT.")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 3 + 4, "Fotocopia P. PROVISIONAL.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 3 + 4, "Croquis de Ubicación.")

    canvas.setFont('Times-BoldItalic', 12)
    canvas.drawString(
        ml, 160, '• Declaro bajo juramento no tener ni registrar antecedentes policiales, ni judiciales.')
    canvas.drawString(
        ml, 145, '• Cumplir con las obligaciones y reglamento interno de la empresa, caso contrario ')
    canvas.drawString(
        ml + 8, 130, 'acepto a que se me imponga las condiciones y sanciones contempladas.')

    canvas.setDash(1, 1)
    canvas.line(ml + 20, 80, ml + 20 + 122, 80)
    canvas.line(ml + 20 * 2 + 122, 80, ml + 20 * 2 + 122 * 2, 80)
    canvas.line(ml + 20 * 3 + 122 * 2, 80, ml + 20 * 3 + 122 * 3, 80)

    canvas.setDash(2, 2)
    canvas.line(ml + 20 + 21, 55, ml + 20 + 21 + 80, 55)
    canvas.line(ml + 20 + 21 * 4 + 80, 55, ml + 20 + 21 * 4 + 80 * 2, 55)
    # canvas.line(ml + 20 + 21*7 + 80*2, 55, ml + 20 + 21*7 + 80*3, 55)

    canvas.setFillColor(black)
    canvas.setFont('Times-Bold', 9)
    canvas.drawString(ml + 20, 55, 'DNI')
    canvas.drawString(ml + 20 + 21 * 4 + 80 - 21, 55, 'DNI')
    canvas.drawString(ml + 20 + 21 * 7 + 80 * 2 - 21, 55, 'TAXI TURISMO AREQUIPA')
    canvas.setFont('Times-Roman', 11)

    canvas.drawString(ml + 20 + 21 * 2, 70, 'Propietario')
    canvas.drawString(ml + 20 + 21 * 5 + 80, 70, 'Cónyuge')
    canvas.drawString(ml + 20 + 21 * 8 + 80 * 2, 70, 'VºBº')

    canvas.rotate(90)
    # canvas.rect(ml, 570, 42, 60, stroke=1, fill=1)
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(570 + 4, -ml - 20 - 4, "DOMICILIO")
    canvas.setFont('Times-Roman', 12)
    canvas.drawString(580 + 4, -ml - 20 * 3 - 7, "REAL")

    canvas.showPage()
    canvas.save()
    response.write(buffer.getvalue())
    buffer.close()
    return response


def print_programming_guide(request, pk=None, guide=None):
    # Configuración de página A5
    A5 = (5.8 * inch, 8.3 * inch)
    ml = 0.4 * inch  # Margen izquierdo
    mr = 0.4 * inch  # Margen derecho
    mt = 0.4 * inch  # Margen superior
    mb = 0.4 * inch  # Margen inferior
    w = A5[0] - ml - mr  # Ancho disponible
    h = A5[1] - mt - mb  # Alto disponible

    # Obtener objeto programming y guide
    programming_obj = Programming.objects.get(id=pk)
    guide_obj = Guide.objects.filter(programming=programming_obj, id=guide).first()

    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
    styles.add(ParagraphStyle(
        name='Left_title',
        parent=styles['Left'],
        fontSize=12,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='Left_subtitle',
        parent=styles['Left'],
        fontSize=8,
        textColor=colors.black,
        fontName='Helvetica'
    ))

    # Crear el encabezado
    header_data = [
        [Paragraph('VICTORIA JUAN GAS', styles['Left_title']),
         Paragraph('SOCIEDAD ANÓNIMA CERRADA', styles['Center']),
         Paragraph('Direc. Car. Panamericana Sur, Km 1113', styles['Right'])],
        [Paragraph('', styles['Left']),
         Paragraph('SICUANI - CANCHIS CUSCO', styles['Center']),
         Paragraph('Asoc. Granjeros Forestales el P. Mzna. D - Lote 8-9', styles['Right'])],
        [Paragraph('', styles['Left']),
         Paragraph('YURA - AREQUIPA - AREQUIPA', styles['Center']),
         Paragraph('', styles['Right'])]
    ]

    header_table = Table(header_data, colWidths=[w / 3.0] * 3)
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Fechas
    date_data = [
        [Paragraph('Fecha de Emisión:', styles['Left_subtitle']),
         Paragraph(programming_obj.departure_date.strftime("%d.%m.%Y") if programming_obj.departure_date else '',
                   styles['Left']),
         Paragraph('Fecha de inicio de Traslado:', styles['Left_subtitle']),
         Paragraph(programming_obj.arrival_date.strftime("%d.%m.%Y") if programming_obj.arrival_date else '',
                   styles['Left'])],
    ]

    date_table = Table(date_data, colWidths=[w / 4.0] * 4)
    date_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # RUC
    ruc_data = [
        [Paragraph('RUC: 20450509125', styles['Left_subtitle']),
         Paragraph('GUIA DE REMISION', styles['Center']),
         Paragraph('REMITENTE', styles['Right'])],
        [Paragraph(f'{guide_obj.serial} - Nº {guide_obj.code}', styles['Left']),
         Paragraph('', styles['Center']),
         Paragraph('', styles['Right'])]
    ]

    ruc_table = Table(ruc_data, colWidths=[w / 3.0] * 3)
    ruc_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Origen y Destino
    origin_destiny_data = [
        [Paragraph('Punto de Partida:', styles['Left_subtitle']),
         Paragraph(programming_obj.get_origin().name, styles['Left']),
         Paragraph('Punto de Llegada:', styles['Left_subtitle']),
         Paragraph(programming_obj.get_destiny().name, styles['Left'])],
    ]

    origin_destiny_table = Table(origin_destiny_data, colWidths=[w / 4.0] * 4)
    origin_destiny_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Traslado
    traslado_data = [
        [Paragraph('Fecha de Inicio de Traslado:', styles['Left_subtitle']),
         Paragraph(programming_obj.arrival_date.strftime("%d.%m.%Y") if programming_obj.arrival_date else '',
                   styles['Left']),
         Paragraph('Costo minimo S/', styles['Left_subtitle']),
         Paragraph(str(guide_obj.minimal_cost) if guide_obj.minimal_cost else '', styles['Left']),
         Paragraph('NOMBRE O RAZON SOCIAL DEL DESTINATARIO', styles['Left_subtitle']),
         Paragraph('', styles['Left'])],
        [Paragraph('Número de RUC:', styles['Left_subtitle']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left'])]
    ]

    traslado_table = Table(traslado_data, colWidths=[w / 6.0] * 6)
    traslado_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Vehículo y Piloto
    vehicle_pilot_data = [
        [Paragraph('Marca y Número de Placa:', styles['Left_subtitle']),
         Paragraph(programming_obj.truck.license_plate if programming_obj.truck else '', styles['Left']),
         Paragraph('Nº de Constancia de Inscripción:', styles['Left_subtitle']),
         Paragraph('', styles['Left']),
         Paragraph('Nº(s) de Licencia(s) de Conducir:', styles['Left_subtitle']),
         Paragraph('', styles['Left'])],
        [Paragraph('UNIDAD DE TRANSPORTE Y CONDUCTOR', styles['Left_subtitle']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left']),
         Paragraph('', styles['Left'])]
    ]

    vehicle_pilot_table = Table(vehicle_pilot_data, colWidths=[w / 6.0] * 6)
    vehicle_pilot_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Detalles
    detail_header = [
        [Paragraph('ITEM', styles['Left_subtitle']),
         Paragraph('DESCRIPCION', styles['Left_subtitle']),
         Paragraph('CANTIDAD', styles['Left_subtitle']),
         Paragraph('UNID. MEDIDA', styles['Left_subtitle']),
         Paragraph('PESO TOTAL', styles['Left_subtitle']),
         Paragraph('', styles['Left'])]
    ]

    detail_header_table = Table(detail_header, colWidths=[w / 6.0] * 6)
    detail_header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Detalles de la guía
    details = GuideDetail.objects.filter(guide=guide_obj)
    detail_rows = []
    for detail in details:
        detail_data = [
            Paragraph(str(detail.id), styles['Left']),
            Paragraph(detail.product.name if detail.product else '', styles['Left']),
            Paragraph(str(detail.quantity), styles['Right']),
            Paragraph(detail.unit_measure.description if detail.unit_measure else '', styles['Left']),
            Paragraph(str(detail.weight), styles['Right']),
            Paragraph('', styles['Left'])
        ]
        detail_rows.append(detail_data)

    if detail_rows:
        detail_table = Table(detail_rows, colWidths=[w / 6.0] * 6)
        detail_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

    # Construir el documento
    elements = []
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(date_table)
    elements.append(Spacer(1, 10))
    elements.append(ruc_table)
    elements.append(Spacer(1, 10))
    elements.append(origin_destiny_table)
    elements.append(Spacer(1, 10))
    elements.append(traslado_table)
    elements.append(Spacer(1, 10))
    elements.append(vehicle_pilot_table)
    elements.append(Spacer(1, 10))
    elements.append(detail_header_table)
    if detail_rows:
        elements.append(detail_table)

    # Generar PDF
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A5,
        rightMargin=mr,
        leftMargin=ml,
        topMargin=mt,
        bottomMargin=mb,
        title=f"Guia de remision [{guide_obj.serial}-{guide_obj.code}]"
    )

    doc.build(elements)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="guia_de_remision_{guide_obj.serial}-{guide_obj.code}.pdf"'
    response.write(buff.getvalue())
    buff.close()

    return response

    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 39 + 3, unit_measure1)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 39 + 3, weight1)

    item2 = ''
    description2 = ''
    quantity2 = ''
    unit_measure2 = ''
    weight2 = ''
    if guide_obj.guidedetail_set.count() > 1:
        item2 = str(guide_obj.guidedetail_set.all()[1].id)
        description2 = str(guide_obj.guidedetail_set.all()[1].product.name)
        quantity2 = str(guide_obj.guidedetail_set.all()[1].quantity)
        unit_measure2 = str(guide_obj.guidedetail_set.all()[1].unit_measure.description)
        weight2 = str(guide_obj.guidedetail_set.all()[1].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 29 + 3, item2)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 29 + 3, description2)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 29 + 3, quantity2)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 29 + 3, unit_measure2)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 29 + 3, weight2)

    item3 = ''
    description3 = ''
    quantity3 = ''
    unit_measure3 = ''
    weight3 = ''
    if guide_obj.guidedetail_set.count() > 2:
        item3 = str(guide_obj.guidedetail_set.all()[2].id)
        description3 = str(guide_obj.guidedetail_set.all()[2].product.name)
        quantity3 = str(guide_obj.guidedetail_set.all()[2].quantity)
        unit_measure3 = str(guide_obj.guidedetail_set.all()[2].unit_measure.description)
        weight3 = str(guide_obj.guidedetail_set.all()[2].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 19 + 3, item3)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 19 + 3, description3)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 19 + 3, quantity3)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 19 + 3, unit_measure3)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 19 + 3, weight3)

    item4 = ''
    description4 = ''
    quantity4 = ''
    unit_measure4 = ''
    weight4 = ''
    if guide_obj.guidedetail_set.count() > 3:
        item4 = str(guide_obj.guidedetail_set.all()[3].id)
        description4 = str(guide_obj.guidedetail_set.all()[3].product.name)
        quantity4 = str(guide_obj.guidedetail_set.all()[3].quantity)
        unit_measure4 = str(guide_obj.guidedetail_set.all()[3].unit_measure.description)
        weight4 = str(guide_obj.guidedetail_set.all()[3].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 9 + 3, item4)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 9 + 3, description4)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 9 + 3, quantity4)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 9 + 3, unit_measure4)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 9 + 3, weight4)

    item5 = ''
    description5 = ''
    quantity5 = ''
    unit_measure5 = ''
    weight5 = ''

    if guide_obj.guidedetail_set.count() > 4:
        item5 = str(guide_obj.guidedetail_set.all()[4].id)
        description5 = str(guide_obj.guidedetail_set.all()[4].product.name)
        quantity5 = str(guide_obj.guidedetail_set.all()[4].quantity)
        unit_measure5 = str(guide_obj.guidedetail_set.all()[4].unit_measure.description)
        weight5 = str(guide_obj.guidedetail_set.all()[4].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 - 1 + 3, item5)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 - 1 + 3, description5)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 - 1 + 3, quantity5)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 - 1 + 3, unit_measure5)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 - 1 + 3, weight5)

    item6 = ''
    description6 = ''
    quantity6 = ''
    unit_measure6 = ''
    weight6 = ''

    if guide_obj.guidedetail_set.count() > 5:
        item6 = str(guide_obj.guidedetail_set.all()[5].id)
        description6 = str(guide_obj.guidedetail_set.all()[5].product.name)
        quantity6 = str(guide_obj.guidedetail_set.all()[5].quantity)
        unit_measure6 = str(guide_obj.guidedetail_set.all()[5].unit_measure.description)
        weight6 = str(guide_obj.guidedetail_set.all()[5].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 - 11 + 3, item6)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 - 11 + 3, description6)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 - 11 + 3, quantity6)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 - 11 + 3, unit_measure6)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 - 11 + 3, weight6)

    item7 = ''
    description7 = ''
    quantity7 = ''
    unit_measure7 = ''
    weight7 = ''

    if guide_obj.guidedetail_set.count() > 6:
        item7 = str(guide_obj.guidedetail_set.all()[6].id)
        description7 = str(guide_obj.guidedetail_set.all()[6].product.name)
        quantity7 = str(guide_obj.guidedetail_set.all()[6].quantity)
        unit_measure7 = str(guide_obj.guidedetail_set.all()[6].unit_measure.description)
        weight7 = str(guide_obj.guidedetail_set.all()[6].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 - 21 + 3, item7)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 - 21 + 3, description7)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 - 21 + 3, quantity7)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 - 21 + 3, unit_measure7)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 - 21 + 3, weight7)

    canvas.drawString(ml + 100 + 3 + 6, mi + 0 - 70 + 6 + 20, 'MOTIVO DEL')
    canvas.drawString(ml + 100 + 3 + 6, mi + 0 - 70 + 6 + 10, 'TRASLADO')

    canvas.drawString(ml + 100 + 3 + 6 + 60, mi + 0 - 73 + 6 + 28, 'Venta')
    canvas.drawString(ml + 100 + 3 + 6 + 60, mi + 0 - 72 + 6 + 13, 'Venta sujeta a')

    canvas.acroForm.checkbox(
        name='CB0',
        checked=False,
        x=ml + 100 + 3 + 6 + 120, y=mi + 0 - 71 + 6 + 25,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB02',
        checked=False,
        x=ml + 100 + 3 + 6 + 120, y=mi + 0 - 71 + 6 + 10,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)

    canvas.drawString(ml + 100 + 3 + 6 + 140, mi + 0 - 73 + 6 + 28, 'Consignación')
    canvas.drawString(ml + 100 + 3 + 6 + 140, mi + 0 - 73 + 6 + 13, 'Devolución')

    canvas.acroForm.checkbox(
        name='CB04',
        checked=False,
        x=ml + 100 + 3 + 6 + 230, y=mi + 0 - 71 + 6 + 25,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB05',
        checked=False,
        x=ml + 100 + 3 + 6 + 230, y=mi + 0 - 71 + 6 + 10,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)

    canvas.drawString(ml + 100 + 3 + 6 + 250, mi + 0 - 73 + 6 + 28, 'Para transformación')
    canvas.drawString(ml + 100 + 3 + 6 + 250, mi + 0 - 73 + 6 + 13, 'Entre establecimientos')

    canvas.acroForm.checkbox(
        name='CB03',
        checked=False,
        x=ml + 100 + 3 + 6 + 335, y=mi + 0 - 71 + 6 + 25,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)

    canvas.acroForm.checkbox(
        name='CB07',
        checked=False,
        x=ml + 100 + 3 + 6 + 335, y=mi + 0 - 71 + 6 + 10,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.drawString(ml + 100 + 3 + 6 + 350, mi + 0 - 73 + 6 + 28, 'Zona primaria')
    canvas.drawString(ml + 100 + 3 + 6 + 350, mi + 0 - 73 + 6 + 13, 'Compra')

    canvas.acroForm.checkbox(
        name='CB8',
        checked=False,
        x=ml + 100 + 3 + 6 + 410, y=mi + 0 - 71 + 6 + 25,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB06',
        checked=False,
        x=ml + 100 + 3 + 6 + 410, y=mi + 0 - 71 + 6 + 10,
        size=7,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)

    canvas.showPage()
    canvas.save()
    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="owners_and_vehicles_update.pdf"'
    r['Content-Disposition'] = 'attachment; filename="guia_de_remision[{} - {}].pdf"'.format(
        guide_obj.serial, guide_obj.code)
    r.write(buff.getvalue())
    buff.close()
    return r


def get_input_note(self, pk=None):
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    details = []
    colspan_headings = ('ARTÍCULOS', '', '', '', '', 'VALORES', '')
    headings = ('Id', 'Codigo', 'Descrición', 'Cant.', 'U. Med.', 'Unitario', 'Total')
    all_details = [(g.id, g.product.id, g.product.name, g.quantity, g.unit_measure.name,
                    g.product.calculate_minimum_unit(), g.product.calculate_minimum_unit() * g.quantity)
                   for g in GuideDetail.objects.filter(guide__id=pk)]
    guide_obj = Guide.objects.get(id=pk)

    footer1 = ('NOTA:', '', 'INGRESO DE BIENES', '', '', '', '')
    footer2 = ('SON:', '', numero_a_moneda(guide_obj.minimal_cost),
               '', '', 'TOTAL S/', str(guide_obj.minimal_cost))
    # t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2])
    t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2],
              colWidths=[0.5 * inch, 0.8 * inch, 1.6 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch])

    t.setStyle(TableStyle(
        [
            ('SPAN', (0, 0), (4, 0)),
            ('SPAN', (5, 0), (6, 0)),
            ('ALIGN', (0, 0), (4, 0), 'CENTER'),
            ('ALIGN', (5, 0), (6, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Newgot'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (1, -2), 'Helvetica-Bold'),
            ('FONTNAME', (5, -1), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (5, -1), (6, -1), 'RIGHT'),
            ('FONTSIZE', (0, -1), (6, -1), 8),
            ('FONTSIZE', (0, -2), (6, -2), 8),
            ('SPAN', (0, -1), (1, -1)),
            ('SPAN', (2, -1), (4, -1)),
            ('SPAN', (0, -2), (1, -2)),
            ('SPAN', (2, -2), (6, -2)),
            ('FONTNAME', (3, 2), (3, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (5, 2), (5, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (6, 2), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 2), (5, -1), 'RIGHT'),
            ('ALIGN', (6, 2), (6, -1), 'RIGHT'),
        ]
    ))

    buff = io.BytesIO()

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title="Reporte Nota de Entrada - [{}-{}]".format(
                                guide_obj.get_serial(), guide_obj.code),
                            )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
                              leading=13, fontName='Newgot', fontSize=12))
    styles.add(ParagraphStyle(name='header2', alignment=TA_CENTER,
                              leading=13, fontName='Helvetica', fontSize=8))
    styles.add(ParagraphStyle(name='header1', alignment=TA_CENTER,
                              leading=13, fontName='Helvetica-Bold', fontSize=12))

    header1 = Paragraph("VICTORIA JUAN GAS", styles['header2'])
    header2 = Paragraph("NOTA DE ENTRADA AL ALMACÉN", styles['header1'])

    Story = []

    Story.append(header1)
    Story.append(Spacer(1, 10))
    Story.append(header2)
    Story.append(Spacer(1, 1))
    Story.append(InputGetContext(pk=pk))
    Story.append(Spacer(1, 1))
    Story.append(t)

    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="nota_de_entrada_[{} - {}].pdf"'.format(
        guide_obj.get_serial(), guide_obj.code)

    doc.build(Story)
    r.write(buff.getvalue())
    buff.close()
    return r


class InputGetContext(Flowable):
    def __init__(self, width=200, height=80, pk=None):
        self.width = width
        self.height = height
        self.pk = pk

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        guide_obj = Guide.objects.get(id=self.pk)
        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        # canvas.rect(0, 8, self.width, self.height, fill=0)
        canvas.setFillColor(white)
        canvas.rect(-12 + 347, 90, 90, 30, fill=1)
        canvas.line(-12 + 347, 90 + 15, -12 + 347 + 90, 90 + 15)
        canvas.line(-12 + 347 + 30, 90, -12 + 347 + 30, 90 + 30)  # vertical
        canvas.line(-12 + 347 + 60, 90, -12 + 347 + 60, 90 + 30)  # vertical
        canvas.roundRect(-12, 5, 437, 65, 4, stroke=1, fill=1)
        # canvas.roundRect(-10, 5, 430, 43, 4, stroke=1, fill=1)
        canvas.setFillColor(black)
        # canvas.setFont('Helvetica', 8)
        canvas.setFont('Helvetica-Bold', 8)
        destiny = guide_obj.route_set.get(type='D')
        canvas.drawString(-12 + 15, 5 + 45, 'PROCEDENCIA: ' + guide_obj.subsidiary.name.upper())
        canvas.drawString(-12 + 15, 5 + 30, 'DESTINO: ' + destiny.subsidiary_store.name.upper())
        canvas.drawString(-12 + 15, 5 + 15, 'SEGÚN: ' + guide_obj.get_serial() +
                          '-' + guide_obj.code + '-' + guide_obj.guide_motive.description.upper())
        canvas.drawString(-12 + 347, 90 + 30 + 2, 'Nro ' + str(guide_obj.id))

        canvas.drawString(-12 + 347 + 5, 90 + 15 + 2, 'Día')
        canvas.drawString(-12 + 347 + 30 + 5, 90 + 15 + 2, 'Mes')
        canvas.drawString(-12 + 347 + 60 + 5, 90 + 15 + 2, 'Año')

        canvas.drawString(-12 + 347 + 10, 90 + 5, str(guide_obj.created_at.day))
        canvas.drawString(-12 + 347 + 40, 90 + 5, str(guide_obj.created_at.month))
        canvas.drawString(-12 + 347 + 65, 90 + 5, str(guide_obj.created_at.year))

        canvas.restoreState()


def get_output_note(self, pk=None):
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    details = []
    colspan_headings = ('ARTÍCULOS', '', '', '', '', 'VALORES', '')
    headings = ('Id', 'Codigo', 'Descrición', 'Cant.', 'U. Med.', 'Unitario', 'Total')
    all_details = [(g.id, g.product.id, g.product.name, g.quantity, g.unit_measure.name,
                    g.product.calculate_minimum_unit(), g.product.calculate_minimum_unit() * g.quantity)
                   for g in GuideDetail.objects.filter(guide__id=pk)]
    guide_obj = Guide.objects.get(id=pk)

    footer1 = ('NOTA:', '', 'INGRESO DE BIENES', '', '', '', '')
    footer2 = (
        'SON:', '', numero_a_moneda(guide_obj.minimal_cost), '', '', 'TOTAL S/', str(guide_obj.minimal_cost))
    # t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2])
    t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2],
              colWidths=[0.5 * inch, 0.8 * inch, 1.6 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch])

    t.setStyle(TableStyle(
        [
            ('SPAN', (0, 0), (4, 0)),
            ('SPAN', (5, 0), (6, 0)),
            ('ALIGN', (0, 0), (4, 0), 'CENTER'),
            ('ALIGN', (5, 0), (6, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Newgot'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (1, -2), 'Helvetica-Bold'),
            ('FONTNAME', (5, -1), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (5, -1), (6, -1), 'RIGHT'),
            ('FONTSIZE', (0, -1), (6, -1), 8),
            ('FONTSIZE', (0, -2), (6, -2), 8),
            ('SPAN', (0, -1), (1, -1)),
            ('SPAN', (2, -1), (4, -1)),
            ('SPAN', (0, -2), (1, -2)),
            ('SPAN', (2, -2), (6, -2)),
            ('FONTNAME', (3, 2), (3, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (5, 2), (5, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (6, 2), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 2), (5, -1), 'RIGHT'),
            ('ALIGN', (6, 2), (6, -1), 'RIGHT'),
        ]
    ))

    buff = io.BytesIO()

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title="Reporte Nota de Salida - [{}-{}]".format(
                                guide_obj.get_serial(), guide_obj.code),
                            )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
                              leading=13, fontName='Newgot', fontSize=12))
    styles.add(
        ParagraphStyle(name='header2', alignment=TA_CENTER, leading=13, fontName='Helvetica', fontSize=8))
    styles.add(
        ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))

    header1 = Paragraph("VICTORIA JUAN GAS", styles['header2'])
    header2 = Paragraph("NOTA DE SALIDA AL ALMACÉN", styles['header1'])

    Story = []

    Story.append(header1)
    Story.append(Spacer(1, 10))
    Story.append(header2)
    Story.append(Spacer(1, 1))
    Story.append(OutputGetContext(pk=pk))
    Story.append(Spacer(1, 1))
    Story.append(t)

    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="nota_de_salida_[{} - {}].pdf"'.format(
        guide_obj.get_serial(), guide_obj.code)

    doc.build(Story)
    r.write(buff.getvalue())
    buff.close()
    return r


class OutputGetContext(Flowable):

    def __init__(self, width=200, height=80, pk=None):
        self.width = width
        self.height = height
        self.pk = pk

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        guide_obj = Guide.objects.get(id=self.pk)
        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        # canvas.rect(0, 8, self.width, self.height, fill=0)
        canvas.setFillColor(white)
        canvas.rect(-12 + 347, 90, 90, 30, fill=1)
        canvas.line(-12 + 347, 90 + 15, -12 + 347 + 90, 90 + 15)
        canvas.line(-12 + 347 + 30, 90, -12 + 347 + 30, 90 + 30)  # vertical
        canvas.line(-12 + 347 + 60, 90, -12 + 347 + 60, 90 + 30)  # vertical
        canvas.roundRect(-12, 5, 437, 65, 4, stroke=1, fill=1)
        # canvas.roundRect(-10, 5, 430, 43, 4, stroke=1, fill=1)
        canvas.setFillColor(black)
        # canvas.setFont('Helvetica', 8)
        canvas.setFont('Helvetica-Bold', 8)
        origin = guide_obj.route_set.get(type='O')
        subsidiary_destiny = '-'
        subsidiary_store_destiny = '-'
        destiny_set = guide_obj.route_set.filter(type='D')
        if destiny_set.count() > 0:
            subsidiary_destiny = destiny_set.last().subsidiary_store.subsidiary.name.upper()
            subsidiary_store_destiny = destiny_set.last().subsidiary_store.name.upper()

        canvas.drawString(-12 + 15, 5 + 45, 'PROCEDENCIA/SALIDA: ' +
                          origin.subsidiary_store.subsidiary.name.upper() + ' - ' + origin.subsidiary_store.name.upper())
        canvas.drawString(-12 + 15, 5 + 30, 'DESTINO: ' +
                          subsidiary_destiny + ' - ' + subsidiary_store_destiny)
        canvas.drawString(-12 + 15, 5 + 15, 'SEGÚN: ' + guide_obj.get_serial() +
                          '-' + guide_obj.code + '-' + guide_obj.guide_motive.description.upper())

        canvas.drawString(-12 + 347, 90 + 30 + 2, 'Nro ' + str(guide_obj.id))

        canvas.drawString(-12 + 347 + 5, 90 + 15 + 2, 'Día')
        canvas.drawString(-12 + 347 + 30 + 5, 90 + 15 + 2, 'Mes')
        canvas.drawString(-12 + 347 + 60 + 5, 90 + 15 + 2, 'Año')

        canvas.drawString(-12 + 347 + 10, 90 + 5, str(guide_obj.created_at.day))
        canvas.drawString(-12 + 347 + 40, 90 + 5, str(guide_obj.created_at.month))
        canvas.drawString(-12 + 347 + 65, 90 + 5, str(guide_obj.created_at.year))

        canvas.restoreState()


def transfer_print(request, pk=None):
    """Genera PDF A5 de la transferencia entre almacenes (serie y correlativo)."""
    from django.shortcuts import get_object_or_404
    from reportlab.lib.pagesizes import A5
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Narrow', 'Arial Narrow.ttf'))
    pdfmetrics.registerFont(TTFont('Narrow-b', 'ARIALNB.TTF'))

    transfer = get_object_or_404(
        Transfer.objects.select_related('origin_store', 'destination_store', 'guide_motive').prefetch_related('details__product', 'details__unit'),
        pk=pk
    )

    buff = io.BytesIO()
    w, h = A5
    margin_lr = 12
    margin_tb = 16
    doc = SimpleDocTemplate(
        buff,
        pagesize=A5,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_tb,
        bottomMargin=margin_tb,
    )
    elements = []

    num_doc = (transfer.serial or 'TRA') + '-' + (transfer.correlative or str(transfer.id).zfill(5))
    dark_blue = colors.HexColor('#1e3a5f')
    light_blue = colors.HexColor('#e3f2fd')

    title_style = ParagraphStyle(
        name='TransferTitle',
        alignment=TA_CENTER,
        fontName='Narrow-b',
        fontSize=13,
        spaceAfter=2,
        textColor=dark_blue,
    )
    sub_style = ParagraphStyle(
        name='TransferSub',
        alignment=TA_CENTER,
        fontName='Narrow',
        fontSize=8,
        spaceAfter=8,
        textColor=colors.HexColor('#5c6bc0'),
    )
    num_style = ParagraphStyle(
        name='TransferNum',
        alignment=TA_CENTER,
        fontName='Narrow-b',
        fontSize=11,
        spaceAfter=12,
        textColor=dark_blue,
    )
    label_style = ParagraphStyle(
        name='TransferLabel',
        alignment=TA_LEFT,
        fontName='Narrow-b',
        fontSize=7,
        spaceAfter=0,
    )
    value_style = ParagraphStyle(
        name='TransferValue',
        alignment=TA_LEFT,
        fontName='Narrow',
        fontSize=7,
        spaceAfter=0,
    )
    product_cell_style = ParagraphStyle(
        name='ProductCell',
        alignment=TA_LEFT,
        fontName='Narrow',
        fontSize=7,
        leading=8,
        leftIndent=2,
        rightIndent=2,
    )

    # Encabezado
    elements.append(Paragraph('TRANSFERENCIA ENTRE ALMACENES', title_style))
    elements.append(Paragraph('Documento de salida de mercadería', sub_style))
    elements.append(Paragraph('Nº ' + num_doc, num_style))
    elements.append(Spacer(1, 2))

    # Datos
    sent_date = transfer.sent_at or transfer.created_at
    date_str = sent_date.strftime('%d/%m/%Y %H:%M') if sent_date else '—'
    origin_name = (transfer.origin_store.name if transfer.origin_store else '—').upper()
    dest_name = (transfer.destination_store.name if transfer.destination_store else '—').upper()
    motive_name = (transfer.guide_motive.description if transfer.guide_motive else '—').upper()

    data_rows = [
        [Paragraph('Fecha de envío', label_style), Paragraph(date_str, value_style)],
        [Paragraph('Almacén origen', label_style), Paragraph(origin_name, value_style)],
        [Paragraph('Almacén destino', label_style), Paragraph(dest_name, value_style)],
        [Paragraph('Motivo', label_style), Paragraph(motive_name, value_style)],
    ]
    usable_width_cm = (w - 2 * margin_lr) / 28.35
    t_info = Table(data_rows, colWidths=[2.6 * cm, (usable_width_cm - 2.6) * cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # Tabla de detalle: Producto como Paragraph para que haga wrap. Cabecera más pequeña; Cant/Und un poco más anchas; Cant resaltada y 0 decimales
    col_item = 0.85 * cm
    col_cant = 1.2 * cm
    col_und = 1.1 * cm
    col_punit = 1.5 * cm
    col_total = 1.5 * cm
    col_product = (usable_width_cm - (col_item / cm) - (col_cant / cm) - (col_und / cm) - (col_punit / cm) - (col_total / cm)) * cm
    col_widths = [col_item, col_product, col_cant, col_und, col_punit, col_total]

    head_font_size = 6
    head_item_style = ParagraphStyle(
        name='HeadItem',
        alignment=TA_CENTER,
        fontName='Narrow-b',
        fontSize=head_font_size,
        textColor=white,
    )
    head_product_style = ParagraphStyle(
        name='HeadProduct',
        alignment=TA_LEFT,
        fontName='Narrow-b',
        fontSize=head_font_size,
        textColor=white,
        leftIndent=3,
    )
    head_right_style = ParagraphStyle(
        name='HeadRight',
        alignment=TA_RIGHT,
        fontName='Narrow-b',
        fontSize=head_font_size,
        textColor=white,
        rightIndent=3,
    )
    rows_data = [[
        Paragraph('Item', head_item_style),
        Paragraph('Producto', head_product_style),
        Paragraph('Cant.', head_right_style),
        Paragraph('Und.', head_right_style),
        Paragraph('P. unit.', head_right_style),
        Paragraph('Total', head_right_style),
    ]]
    # Estilo para cantidad: alineado a la derecha y resaltado (se aplica fondo por TableStyle)
    cell_cant_style = ParagraphStyle(
        name='CellCant',
        alignment=TA_RIGHT,
        fontName='Narrow',
        fontSize=7,
        leading=8,
        rightIndent=3,
    )
    cell_right_style = ParagraphStyle(
        name='CellRight',
        alignment=TA_RIGHT,
        fontName='Narrow',
        fontSize=7,
        leading=8,
        rightIndent=3,
    )
    for i, d in enumerate(transfer.details.all(), 1):
        unit_name = d.unit.name if d.unit else 'UND'
        product_name = (d.product.name or '—').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        qty_int = int(round(float(d.quantity), 0))
        rows_data.append([
            Paragraph(str(i), product_cell_style),
            Paragraph(product_name, product_cell_style),
            Paragraph(str(qty_int), cell_cant_style),
            Paragraph(unit_name, cell_right_style),
            Paragraph(str(round(float(d.unit_price), 2)), cell_right_style),
            Paragraph(str(round(float(d.total), 2)), cell_right_style),
        ])
    total_gral = sum(d.total for d in transfer.details.all())
    total_style = ParagraphStyle(name='TotalCell', alignment=TA_RIGHT, fontName='Narrow-b', fontSize=7)
    rows_data.append([
        '', '', '', '',
        Paragraph('TOTAL S/', total_style),
        Paragraph(str(round(float(total_gral), 2)), total_style),
    ])

    # Fondo resaltado para columna Cantidad (amarillo suave)
    highlight_cant = colors.HexColor('#fff9c4')
    t_detail = Table(rows_data, colWidths=col_widths)
    t_detail.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, 0), head_font_size),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Cant., Und., P. unit., Total
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b0bec5')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, dark_blue),
        ('FONTNAME', (0, 1), (-1, -2), 'Narrow'),
        ('FONTSIZE', (0, 1), (-1, -2), 7),
        ('TOPPADDING', (0, 1), (-1, -2), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -2), 5),
        ('BACKGROUND', (2, 1), (2, -2), highlight_cant),  # Resaltar columna Cantidad
        ('FONTNAME', (4, -1), (-1, -1), 'Narrow-b'),
        ('BACKGROUND', (0, -1), (-1, -1), light_blue),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
    ]))
    elements.append(t_detail)
    elements.append(Spacer(1, 8))

    if transfer.observation:
        obs_label = ParagraphStyle(name='ObsLabel', alignment=TA_LEFT, fontName='Narrow-b', fontSize=7, spaceAfter=2)
        obs_text = (transfer.observation[:250] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph('Observaciones:', obs_label))
        elements.append(Paragraph(obs_text, value_style))
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 4))
    footer_style = ParagraphStyle(name='Foot', alignment=TA_CENTER, fontName='Narrow', fontSize=6, textColor=colors.HexColor('#78909c'))
    elements.append(Paragraph('— ' + num_doc + ' —', footer_style))

    doc.build(elements)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="transferencia_{}.pdf"'.format(num_doc.replace('-', '_'))
    response.write(buff.getvalue())
    buff.close()
    return response


def NumTomonth(shortMonth):
    return {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }[shortMonth]


# def print_ticket(request, pk=None):
#     reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
#     pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
#     pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))
#
#     fuel_programming_obj = FuelProgramming.objects.get(id=int(pk))
#
#     tbh_business_name = (fuel_programming_obj.subsidiary.business_name, '')
#     tbh_address = (fuel_programming_obj.subsidiary.address, '')
#     th = Table([tbh_business_name] + [tbh_address], colWidths=[5.5 * inch, 0.1 * inch])
#     th.setStyle(TableStyle(
#         [
#
#             ('FONTNAME', (0, 0), (0, -1), 'Square'),
#             # ('GRID', (0, 0), (-1, -1), 1, colors.white),
#             ('ALIGN', (0, 0), (0, -1), 'CENTER'),
#             ('FONTNAME', (0, 1), (0, -1), 'Square'),
#             ('FONTSIZE', (0, 0), (0, -1), 12),
#
#             # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
#             # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
#         ]
#     ))
#
#     tpl_supplier = ('ABASTECER EN', fuel_programming_obj.supplier.name, '', '')
#     tpl_date = ('FECHA', str(fuel_programming_obj.date_fuel.day) + ' ' +
#                 str(NumTomonth(fuel_programming_obj.date_fuel.month)) + ' ' + str(fuel_programming_obj.date_fuel.year))
#     tpl_quantity = ('CANTIDAD', str(fuel_programming_obj.quantity_fuel),
#                     str(fuel_programming_obj.unit_fuel.name))
#     tpl_license_plate = ('PLACA', str(fuel_programming_obj.programming.truck.license_plate))
#     tpl_pilot = ('CONDUCTOR', str(fuel_programming_obj.programming.get_pilot().names) + ' ' + str(
#         fuel_programming_obj.programming.get_pilot().paternal_last_name) + ' ' + str(
#         fuel_programming_obj.programming.get_pilot().maternal_last_name))
#     tpl_route = ('RUTA', str(fuel_programming_obj.programming.get_route()))
#     tpl_client = ('PRECIO', 'S/. ' + str(round(fuel_programming_obj.price_fuel, 2)),
#                   'IMPORTE', 'S/. ' + str(round(fuel_programming_obj.amount(), 2)))
#
#     t = Table([tpl_supplier] + [tpl_date] + [tpl_quantity] + [tpl_license_plate] + [tpl_pilot] +
#               [tpl_route] + [tpl_client], colWidths=[0.65 * inch, 0.7 * inch, 0.8 * inch, 0.9 * inch])
#
#     t.setStyle(TableStyle(
#         [
#             ('FONTNAME', (2, 2), (3, 2), 'Newgot'),  # galon
#             ('FONTNAME', (1, 0), (3, 0), 'Newgot'),  # proveedor
#             ('FONTNAME', (1, 5), (3, 5), 'Newgot'),  # ruta
#             # ('FONTNAME', (1, 6), (1, 6), 'Square'),  # tpl_client - price
#             ('FONTNAME', (2, 6), (2, 6), 'Newgot'),  # tpl_client - import
#             ('FONTSIZE', (0, 0), (-1, -1), 7.2),  # tpl_quantity
#             ('FONTSIZE', (1, 0), (3, 0), 8),  # proveeodr
#             ('FONTSIZE', (1, 5), (3, 5), 8),  # ruta
#             ('FONTSIZE', (2, 2), (3, 2), 8),  # galon
#
#             ('SPAN', (1, 0), (3, 0)),
#             ('SPAN', (1, 1), (3, 1)),
#             ('SPAN', (2, 2), (3, 2)),
#             ('SPAN', (1, 3), (3, 3)),
#             ('SPAN', (1, 4), (3, 4)),
#             ('SPAN', (1, 5), (3, 5)),
#             ('FONTNAME', (0, 0), (0, -1), 'Newgot'),
#             # ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),#BORDE COLOR
#             # ('GRID',(0,0),(-1,-1),1,colors.lightgrey)
#             # ('BOX',(0,0),(-1,-1),0.6*mm,(0,0,0))
#             # ('LINEBEFORE',(2,1),(2,-2),6,colors.pink)
#
#             # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
#             # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
#         ]
#     ))
#
#     buff = io.BytesIO()
#
#     xmax = 595
#     ymax = 842
#
#     ml = 0.14 * cm
#     mr = 0.05 * cm
#     ms = 0.1 * cm
#     mi = 0.1 * cm
#
#     doc = SimpleDocTemplate(buff,
#                             pagesize=C7,
#                             rightMargin=mr,
#                             leftMargin=ml,
#                             topMargin=ms,
#                             bottomMargin=mi,
#                             title='Combustible'
#                             )
#
#     styles = getSampleStyleSheet()
#     styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
#                               leading=13, fontName='Newgot', fontSize=12))
#     styles.add(
#         ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))
#
#     Story = []
#
#     Story.append(th)
#     Story.append(Spacer(1, 60))
#     Story.append(t)
#     Story.append(OutputGetTicket(fuel_programming_obj=fuel_programming_obj))
#     Story.append(Spacer(1, 1))
#
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = 'attachment; filename="Combustible_[{}].pdf"'.format(
#         fuel_programming_obj.get_correlative())
#     doc.build(Story)
#     response.write(buff.getvalue())
#     buff.close()
#     return response


class OutputGetTicket(Flowable):

    def __init__(self, width=200, height=80, fuel_programming_obj=None):
        self.width = width
        self.height = height
        self.fuel_programming_obj = fuel_programming_obj

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        fuel_programming_obj = self.fuel_programming_obj

        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFillColor(white)

        trns = Color(0, 0, 200, alpha=0.1)
        canvas.setFillColor(trns)
        canvas.roundRect(120, 240, 80, 18, 3, stroke=1, fill=1)  # rectangulo id
        canvas.line(140, 258, 140, 240)  # vertical

        canvas.roundRect(1, 190, 200, 19, 2, stroke=1, fill=1)  # rectangulo titulo
        canvas.line(42, 209, 42, 190)  # vertical
        canvas.roundRect(1, 80, 200, 107, 2, stroke=1, fill=1)  # rectangulo detalle
        canvas.line(42, 186, 42, 80)  # vertical
        canvas.roundRect(1, 17, 200, 60, 2, stroke=1, fill=1)  # rectangulo firma
        canvas.line(105, 76, 105, 17)

        canvas.setFillColor(black)
        canvas.setFont('Newgot', 9)
        canvas.drawString(126, 246, 'Nº')
        canvas.drawString(150, 246, str(fuel_programming_obj.get_correlative()))

        canvas.drawString(27, 7, 'Firma conductor')
        canvas.drawString(146, 7, 'Firma')
        canvas.setFont('Square', 10)
        canvas.drawString(60, 222, 'VALE DE COMBUSTIBLE')

        canvas.restoreState()


def get_qr(table):
    # generate and rescale QR
    qr_code = qr.QrCodeWidget(table)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(
        2.5 * cm, 2.5 * cm, transform=[2.5 * cm / width, 0, 0, 2.5 * cm / height, 0, 0])
    drawing.add(qr_code)

    return drawing


class DrawInvoice(Flowable):
    def __init__(self, width=200, height=3, count_row=None):
        self.width = width
        self.height = height
        self.count_row = count_row

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        canvas.saveState()

        canvas.setStrokeGray(0.9)
        # canvas.setFillColor(Color(0, 0, 0, alpha=1))
        canvas.setLineWidth(3)
        canvas.roundRect(-7, 1, 563, 84.5, 8, stroke=1, fill=0)
        canvas.restoreState()


def guide(request, pk=None):
    A4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch
    w = 8.3 * inch - 0.25 * inch - 0.25 * inch
    guide_obj = Guide.objects.get(id=pk)
    subsidiary_obj = guide_obj.subsidiary
    client = guide_obj.contract_detail.contract.client.names
    client_type_document = guide_obj.contract_detail.contract.client.clienttype_set.last().document_type.short_description
    client_document_number = guide_obj.contract_detail.contract.client.clienttype_set.last().document_number
    client_obj = guide_obj.client
    client_address = ClientAddress.objects.filter(client=client_obj, type_address='P').last()
    # client_address = guide_obj.contract_detail.contract.client.clientaddress_set.last().address

    date = utc_to_local(guide_obj.date_issue)
    date_transfer = utc_to_local(guide_obj.transfer_date)
    document_type = 'GUÍA DE REMISIÓN ELECTRÓNICA REMITENTE'
    document_number = (str(guide_obj.serial) + '-' + str(guide_obj.correlative).zfill(
        7 - len(str(guide_obj.correlative)))).upper()
    I = Image(logo)
    I.drawHeight = 1.1 * inch / 2.9
    I.drawWidth = 1.1 * inch / 2.9

    header_left_table = [
        [I, 'ANDERQUIN E.I.R.L.'],
        [Paragraph('JR. CARABAYA NRO. 443 (AL FRENTE DE LA PLAZA MANCO CAPAC) PUNO - SAN ROMAN - JULIACA',
                   styles["Left_square_title"]), '']
    ]
    header_l = Table(header_left_table, colWidths=[w * 6 / 100, w * 64 / 100])

    left_header_style = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        # ('TEXTCOLOR', (0, 0), (-1, -1), colors.red)
        ('FONTNAME', (0, 0), (-1, -1), 'All-Star-Resort'),
        ('FONTSIZE', (0, 0), (-1, -1), 20),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('LEFTPADDING', (1, 0), (1, 0), 2),
        ('BOTTOMPADDING', (1, 0), (1, 0), 11),
        ('TOPPADDING', (0, 1), (1, 1), 0),
        ('SPAN', (0, 1), (1, 1))
    ]
    header_l.setStyle(TableStyle(left_header_style))

    business_right = [
        [Paragraph('R.U.C. Nº ' + str(subsidiary_obj.ruc), styles["narrow_a_center"])],
        [Paragraph(document_type, styles["CenterNewgotTitle"])],
        [document_number],
    ]
    D = Table(business_right, rowHeights=[inch * 0.35, inch * 0.35, inch * 0.35])
    document_style = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        # ('SPAN', (0, 0), (0, 0))
    ]
    D.setStyle(TableStyle(document_style))
    H = [
        [header_l, D]
    ]
    document_header = Table(H, colWidths=[w * 70 / 100, w * 30 / 100])
    header_style = [
        ('GRID', (1, 0), (1, 0), 0.9, colors.black),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, 0), 'LEFT'),  # first column
        ('ALIGNMENT', (1, 0), (1, 0), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
        # ('LINEBELOW', (0, -1), (-1, -1), 0.5, purple, 1, None, None, 4, 1),
        # ('BACKGROUND', (0, 0), (-1, 1), HexColor('#0362BB')),  # Establecer el color de fondo de la segunda fila
        # ('LINEBEFORE', (1, 0), (-1, -1), 0.1, colors.grey),
        # Establezca el color de la línea izquierda de la tabla en
    ]
    document_header.setStyle(TableStyle(header_style))

    order_buy = '-'
    if guide_obj.order_buy:
        order_buy = guide_obj.order_buy

    pdf_person = Table(
        [('Fecha de Emisión', ': ' + str(date.strftime("%d/%m/%Y")), 'Doc. Relacionado', 'Nº O/C: ' + order_buy,
          'Doc. Referencia', '')] +
        [('Destinatario', ': ' + client, '', '', 'Doc. Identidad',
          ': ' + client_type_document + ' ' + client_document_number)] +
        [('Dirección', ': ' + client_address.address, '', '', '', '')] +
        [('Ref. Llegada', '', '', '', '', '')],
        colWidths=[w * 15 / 100, w * 10 / 100, w * 20 / 100, w * 20 / 100, w * 17 / 100, w * 18 / 100],
        rowHeights=[inch * 0.18, inch * 0.15, inch * 0.15, inch * 0.18])
    style_person = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-b'),  # all columns
        ('FONTNAME', (1, 0), (1, 3), 'Narrow-a'),  # all columns
        ('FONTNAME', (5, 0), (5, 2), 'Narrow-a'),  # all columns
        ('SPAN', (1, 1), (3, 1)),
        ('SPAN', (1, 2), (5, 2)),
        ('SPAN', (1, 3), (5, 3)),
        # ('FONTNAME', (0, 0), (-1, 0), 'Ticketing'),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('FONTSIZE', (1, 0), (1, 3), 6),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 5),  # all columns
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # all columns
        ('TOPPADDING', (1, 0), (1, 0), 5),  # all columns
        # ('BOTTOMPADDING', (1, 2), (1, 2), 5),  # all columns
        # ('LEFTPADDING', (0, 0), (0, -1), 2),  # first column
        # ('LEFTPADDING', (1, 0), (1, -1), 2),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),  # second column
        # ('BACKGROUND', (1, 2), (5, 2), HexColor('#0362BB')),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.9, colors.black)
    ]
    pdf_person.setStyle(TableStyle(style_person))
    # ----------------------------------------------------------------
    if guide_obj.vehicle is not None and guide_obj.driver is not None:
        pdf_transfer = Table(
            [('Fecha Inicio traslado', ': ' + date_transfer.strftime("%d/%m/%Y"), 'Observaciones', '')] +
            [(Paragraph('Fecha Entrega bienes al transportista', styles["narrow_b_normal_justify"]),
              ': ' + date_transfer.strftime("%d/%m/%Y"), '')] +
            [('Motivo de traslado: ', ': ' + guide_obj.guide_motive.description.upper(), '', '', '', '',
              'Modalidad Traslado', ': ' + 'TRANSPORTE ' + guide_obj.get_modality_transport_display())] +
            [('Transportista: ', ': ' + guide_obj.carrier.name.upper(), '', '', '', '', 'RUC',
              ': ' + guide_obj.carrier.ruc)] +
            [('Placa:', ': ' + guide_obj.vehicle.license_plate.upper(), 'Marca',
              guide_obj.vehicle.truck_model.truck_brand.name if guide_obj.vehicle and guide_obj.vehicle.truck_model and guide_obj.vehicle.truck_model.truck_brand else '',
              'CIMTC', guide_obj.register_mtc, 'Lic. Conducir',
              ': ' + str(guide_obj.driver.n_license))],
            # [('FECHA INICIO DE TRASLADO: ', date_transfer.strftime("%d/%m/%Y"))] +
            # [('MODALIDAD DE TRANSPORTE: ', 'TRANSPORTE ' + guide_obj.get_modality_transport_display())] +
            # [('PESO BRUTO TOTAL (KGM): ', round(decimal.Decimal(guide_obj.weight), 2))] +
            # [('NÚMERO DE BULTOS: ', round(decimal.Decimal(guide_obj.package), 0))],
            colWidths=[w * 15 / 100, w * 10 / 100, w * 10 / 100, w * 15 / 100, w * 6 / 100, w * 14 / 100,
                       w * 13 / 100, w * 17 / 100],
            rowHeights=[inch * 0.18, inch * 0.27, inch * 0.18, inch * 0.18, inch * 0.18])
    else:
        pdf_transfer = Table(
            [('Fecha Inicio traslado', ': ' + date_transfer.strftime("%d/%m/%Y"), 'Observaciones', '')] +
            [(Paragraph('Fecha Entrega bienes al transportista', styles["narrow_b_normal_justify"]),
              ': ' + date_transfer.strftime("%d/%m/%Y"), '')] +
            [('Motivo de traslado: ', ': ' + guide_obj.guide_motive.description.upper(), '', '', '', '',
              'Modalidad Traslado', ': ' + 'TRANSPORTE ' + guide_obj.get_modality_transport_display())] +
            [('Transportista: ', ': ' + guide_obj.carrier.name.upper(), '', '', 'CIMTC', guide_obj.register_mtc, 'RUC',
              ': ' + guide_obj.carrier.ruc)],
            colWidths=[w * 15 / 100, w * 10 / 100, w * 10 / 100, w * 15 / 100, w * 6 / 100, w * 14 / 100,
                       w * 13 / 100, w * 17 / 100],
            rowHeights=[inch * 0.18, inch * 0.27, inch * 0.18, inch * 0.18])

    style_transfer = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-b'),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (1, 0), (1, 4), 'Narrow-a'),
        ('FONTNAME', (3, 0), (3, 4), 'Narrow-a'),
        ('FONTNAME', (7, 0), (7, 4), 'Narrow-a'),
        ('FONTNAME', (3, 4), (3, 4), 'Narrow-a'),
        ('FONTNAME', (5, 4), (5, 4), 'Narrow-a'),
        # ('FONTNAME', (0, 0), (-1, 0), 'Ticketing'),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('FONTSIZE', (1, 0), (1, 4), 6),  # all columns
        ('FONTSIZE', (7, 0), (7, 4), 6),  # all columns
        ('FONTSIZE', (3, 4), (3, 4), 6),  # all columns
        ('FONTSIZE', (5, 4), (5, 4), 6),  # all columns
        ('TOPPADDING', (3, 4), (3, 4), 7),  # all columns
        ('TOPPADDING', (5, 4), (5, 4), 6),  # all columns
        # ('LEFTPADDING', (0, 0), (-1, -1), 2),  # first column
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # second column
        ('ALIGNMENT', (2, 4), (2, 4), 'RIGHT'),  # second column
        ('BOX', (0, 0), (-1, -1), 0.9, colors.black),
        # ('TOPPADDING', (0, 0), (-1, -1), 0),
        # ('BOTTOMPADDING', (0, 0), (-1, -1), -2),
        # ('BACKGROUND', (3, 4), (3, 4), colors.green ),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        # ('TOPPADDING', (0, 0), (-1, 0), 2),
        # ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        # ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#0362BB')),  # all columns
    ]
    pdf_transfer.setStyle(TableStyle(style_transfer))

    pdf_address = Table(
        [('Punto de partida', ': ' + str(guide_obj.origin_address.title()), 'Ubigeo', ': ' + guide_obj.origin)] +
        [('Punto de Llegada', ': ' + str(guide_obj.destiny_address.title()), 'Ubigeo', ': ' + guide_obj.destiny)],
        colWidths=[w * 15 / 100, w * 60 / 100, w * 15 / 100, w * 10 / 100],
        rowHeights=[inch * 0.18, inch * 0.18])
    style_address = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-b'),  # all columns
        ('FONTNAME', (1, 0), (1, 1), 'Narrow-a'),
        ('FONTNAME', (3, 0), (3, 1), 'Narrow-a'),
        # ('FONTNAME', (0, 0), (-1, 0), 'Ticketing'),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('FONTSIZE', (1, 0), (1, 1), 7),
        ('FONTSIZE', (3, 0), (3, 1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOX', (0, 0), (-1, -1), 0.9, colors.black)
        # ('LEFTPADDING', (0, 0), (-1, -1), 2),  # first column
        # ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # second column
        # ('TOPPADDING', (0, 0), (-1, -1), 2),
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        # ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0362BB')),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        # ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#0362BB')),  # all columns
    ]
    pdf_address.setStyle(TableStyle(style_address))

    style_header = [
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-b'),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.9, colors.black),  # all columns
    ]
    pdf_header = Table(
        [('Código', 'Cantidad', 'Unidad', 'Descripción', 'Peso')],
        colWidths=[w * 8 / 100, w * 8 / 100, w * 8 / 100, w * 66 / 100, w * 10 / 100]
    )
    pdf_header.setStyle(TableStyle(style_header))

    row = []
    for d in guide_obj.guidedetail_set.all():
        product = Paragraph(str(d.product.name).upper(),
                            styles["Left-text"])
        code = str(d.product.code)
        unit = str(d.unit.description)
        product_detail_get = ProductDetail.objects.filter(unit=d.unit, product=d.product).last()
        quantity_minimum = product_detail_get.quantity_minimum
        quantity_in_units = d.quantity / quantity_minimum

        quantity = round(decimal.Decimal(quantity_in_units), 2)
        weight = str(round(decimal.Decimal(guide_obj.weight), 2))
        row.append((code, str(d.quantity), unit, product, str(weight) + ' ' + 'KGM'))
    if len(row) <= 0:
        row.append(('', '', '', '', ''))
    pdf_detail = Table(row, colWidths=[w * 8 / 100, w * 8 / 100, w * 8 / 100, w * 66 / 100, w * 10 / 100])

    unique_row = [
        ['', '', '', '', ''],
        [pdf_detail],
        ['', '', '', 'Peso total:', str(round(decimal.Decimal(guide_obj.weight), 2)) + ' ' + 'KGM'],
    ]
    unique_row_table = Table(unique_row, colWidths=[w * 8 / 100, w * 8 / 100, w * 8 / 100, w * 66 / 100, w * 10 / 100],
                             rowHeights=[inch * 0.00, w * 50 / 100, inch * 0.25])

    style_detail_2 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-a'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
    ]
    style_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-a'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 1), (0, 2)),
        ('SPAN', (1, 1), (1, 2)),
        ('SPAN', (2, 1), (2, 2)),
        ('BACKGROUND', (3, 2), (3, 1), HexColor('#0362BB')),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('ALIGNMENT', (3, 2), (3, 2), 'RIGHT'),
        ('ALIGNMENT', (4, 2), (4, 2), 'RIGHT'),
        ('VALIGN', (3, 2), (3, 2), 'MIDDLE'),
        ('VALIGN', (4, 2), (4, 2), 'MIDDLE'),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (3, 2), (3, 2), 3),
        ('RIGHTPADDING', (4, 2), (4, 2), 8),
        ('BOTTOMPADDING', (3, 2), (3, 2), -8),
        ('BOTTOMPADDING', (4, 2), (4, 2), -8),
        ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('LINEABOVE', (3, 2), (3, 2), 1.8, colors.white),
        ('LINEABOVE', (4, 2), (4, 2), 1.8, colors.white),
        ('BOX', (2, 1), (2, 2), 0.9, colors.black),
        ('BOX', (4, 1), (4, 2), 0.9, colors.black)
    ]
    pdf_detail.setStyle(TableStyle(style_detail_2))
    unique_row_table.setStyle(TableStyle(style_detail))

    pdf_observation = 'OBSERVACIÓN: ' + str(guide_obj.observation)

    code_qr = 'https://4soluciones.pse.pe/20600854535'

    qr_left = [
        ['Ind. transbordo programado  : NO'],
        ['Ind. traslado vehiculos de categ. M1 o L : NO'],
        ['Ind. retorno vehi. con envases o embalajes vacíos  : NO'],
        ['Ind. retorno vehiculo vacio  : NO'],
    ]
    qr_center = [
        [pdf_observation]
    ]

    pdf_footer = Paragraph(
        'Representación impresa de la Guía de Remisión Electrónica, para ver el documento visita https://4soluciones.pse.pe/20604193053',
        styles["narrow_a_left_foot"])
    pdf_link_tres = Paragraph('Autorizado mediante Resolución No.034-005-0005315-SUNAT', styles["narrow_a_left_foot"])
    footer = [
        [pdf_footer, pdf_link_tres]
    ]
    table_footer = Table(footer, colWidths=[w * 60 / 100, w * 40 / 100])

    qr_l = Table(qr_left, colWidths=[w * 40 / 100], rowHeights=[inch * 0.15, inch * 0.15, inch * 0.15, inch * 0.15])
    qr_c = Table(qr_center, colWidths=[w * 40 / 100])

    style_qr1 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    qr_l.setStyle(TableStyle(style_qr1))
    qr_c.setStyle(TableStyle(style_qr1))

    qr_row = [
        [get_qr(code_qr), qr_c, qr_l],
    ]
    qr_table = Table(qr_row, colWidths=[w * 16 / 100, w * 44 / 100, w * 40 / 100])
    style_qr = [
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.9, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    qr_table.setStyle(TableStyle(style_qr))

    counter = guide_obj.guidedetail_set.all().count()
    buff = io.BytesIO()

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title=str(guide_obj.serial) + '-' + str(guide_obj.correlative)
                            )
    pdf = []
    pdf.append(document_header)
    pdf.append(Spacer(1, 5))
    pdf.append(pdf_person)
    pdf.append(Spacer(1, 5))
    pdf.append(pdf_transfer)
    pdf.append(Spacer(1, 5))
    pdf.append(pdf_address)
    pdf.append(Spacer(1, 5))
    pdf.append(pdf_header)
    pdf.append(unique_row_table)
    pdf.append(Spacer(1, 5))
    pdf.append(qr_table)
    pdf.append(Spacer(1, 2))
    pdf.append(table_footer)
    doc.build(pdf)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="[{}].pdf"'.format(
        str('Guia:') + str(guide_obj.serial) + str(guide_obj.correlative))
    response.write(buff.getvalue())
    buff.close()
    return response


def picking(request, pk=None):
    A4 = (8.3 * inch, 11.7 * inch)
    ml = 0.4 * inch  # Margen izquierdo
    mr = 0.4 * inch  # Margen derecho
    mt = 0.4 * inch  # Margen superior
    mb = 0.4 * inch  # Margen inferior
    w = A4[0] - ml - mr  # Ancho disponible
    h = A4[1] - mt - mb  # Alto disponible

    # Obtener objeto picking
    picking_obj = Picking.objects.get(id=pk)

    # Crear el encabezado
    header_data = [
        [Paragraph('ANDERQUIN E.I.R.L.', styles['narrow_b_left']),
         Paragraph('REPORTE DE PICKING POR TRANSPORTE', styles['narrow_b_center']),
         Paragraph(f'Fecha: {picking_obj.departure_date.strftime("%d.%m.%Y")}', styles['Right'])],
        [Paragraph('JR. CARABAYA NRO. 443', styles['narrow_a_left']),
         Paragraph(f'Número de Transporte: {str(picking_obj.picking_number).zfill(4)}', styles['Center']),
         Paragraph(f'Hora: {picking_obj.departure_time.strftime("%H:%M:%S") if picking_obj.departure_time else ""}',
                   styles['Right'])],
        [Paragraph('', styles['Left']),
         Paragraph(f'Fecha de Despacho: {picking_obj.departure_date.strftime("%d.%m.%Y")}', styles['Center']),
         Paragraph('Pág: 1', styles['Right'])]
    ]

    header_table = Table(header_data, colWidths=[w * 20 / 100, w * 60 / 100, w * 20 / 100])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        # ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Información del transporte
    transport_data = [
        [Paragraph('Puesto Expedición', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.subsidiary.name if picking_obj.subsidiary else '', styles['narrow_a_left']),
         Paragraph('Clase de transp.', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph('DESP', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left'])],
        [Paragraph('Placa tracto', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.vehicle.license_plate if picking_obj.vehicle else '', styles['narrow_a_left']),
         Paragraph('RUC Transportista', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.carrier.ruc if picking_obj.carrier else '', styles['narrow_a_left']),
         Paragraph('Brevete:', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.driver.n_license if picking_obj.driver else '', styles['narrow_a_left'])],
        [Paragraph('Placas Carretas', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.towing.license_plate if picking_obj.towing else '', styles['narrow_a_left']),
         Paragraph('Razón Social', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.carrier.name if picking_obj.carrier else '', styles['narrow_a_left']),
         Paragraph('Nombre Chofer', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph(picking_obj.driver.names if picking_obj.driver else '', styles['narrow_a_left'])],
        [Paragraph('Almacén', styles['narrow_a_left']),
         Paragraph(':', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left']),
         Paragraph('', styles['narrow_a_left'])]
    ]

    transport_table = Table(transport_data, colWidths=[w * 12 / 100,  # 1
                                                       w * 1 / 100,  # :
                                                       w * 21 / 100,  # 2
                                                       w * 12 / 100,  # 3
                                                       w * 3 / 100,  # :
                                                       w * 23 / 100,  # 4
                                                       w * 10 / 100,  # 4
                                                       w * 3 / 100,  # :
                                                       w * 15 / 100  # 5
                                                       ])
    transport_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        # ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        # ('BACKGROUND',  (5, 0), (5, -1), colors.green),
        ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
        ('LEFTPADDING', (1, 0), (1, -1), -3),
        ('LEFTPADDING', (2, 0), (2, -1), 0),
        ('LEFTPADDING', (4, 0), (4, -1), 0),
        ('LEFTPADDING', (5, 0), (5, -1), -7),
        ('LEFTPADDING', (7, 0), (7, -1), 0),
        ('LEFTPADDING', (8, 0), (8, -1), -7),
    ]))

    # Cabecera de detalles
    detail_header = [
        [Paragraph('Lote', styles['narrow_a_left']),
         Paragraph('Descripción', styles['narrow_a_left']),
         Paragraph('Unidad (CAJA)', styles['narrow_a_right_9']),
         Paragraph('Unidad Base', styles['narrow_a_right_9']),
         Paragraph('Total Carga (Kilos)', styles['narrow_a_right_9'])],

    ]

    detail_header_table = Table(detail_header, colWidths=[w * 5 / 100,
                                                          w * 50 / 100,
                                                          w * 15 / 100,
                                                          w * 15 / 100,
                                                          w * 15 / 100,
                                                          ])
    detail_header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Narrow-a'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        # ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Detalles del picking
    details = PickingDetail.objects.filter(picking=picking_obj)
    detail_rows = []
    total_weight = decimal.Decimal('0.00')

    for detail in details:
        quantity_minimum = decimal.Decimal(0.00)
        product_detail_set = ProductDetail.objects.filter(unit__description='CAJA', product=detail.product)
        if product_detail_set.exists():
            product_detail_obj = product_detail_set.last()
            quantity_minimum = product_detail_obj.quantity_minimum
        if quantity_minimum > 0:
            quantity_box = int(detail.quantity / quantity_minimum)
            quantity_und = round(detail.quantity - (quantity_box * quantity_minimum))
        else:
            quantity_box = decimal.Decimal(0.00)
            quantity_und = round(detail.quantity)
        quantity_in_box = f'{quantity_box} CJ {quantity_und} UND'
        weight_kg = detail.product.weight / 1000
        weight = round(detail.quantity * weight_kg, 2)
        detail_data = [
            Paragraph(detail.batch.batch_number if detail.batch else '', styles['narrow_a_left']),
            Paragraph(f'{detail.product.code} {detail.product.name} ({detail.get_detail_type_display()})', styles['narrow_a_left']),
            Paragraph(f"{quantity_in_box}", styles['narrow_a_right_9']),
            Paragraph(f"{'{:,}'.format(detail.quantity)}", styles['narrow_a_right_9']),
            Paragraph(f"{'{:,}'.format(weight)}", styles['narrow_a_right_9'])
        ]
        detail_rows.append(detail_data)
        total_weight += weight

    detail_table = Table(detail_rows, colWidths=[w * 5 / 100,
                                                 w * 50 / 100,
                                                 w * 15 / 100,
                                                 w * 15 / 100,
                                                 w * 15 / 100,
                                                 ])
    detail_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        # ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Totales
    difference_weight = decimal.Decimal('6000.00') - total_weight
    total_data = [
        ['', '', '', Paragraph('Total', styles['narrow_a_left_8']), ':',
         Paragraph(f"{'{:,}'.format(total_weight)}", styles['narrow_a_right_8'])],
        ['', '', '', Paragraph('Capacidad Camión', styles['narrow_a_left_8']), ':',
         Paragraph('6,000.00', styles['narrow_a_right_8'])],
        ['', '', '', Paragraph('Total Carga', styles['narrow_a_left_8']), ':',
         Paragraph(f"{'{:,}'.format(total_weight)}", styles['narrow_a_right_8'])],
        ['', '', '', Paragraph('Diferencia', styles['narrow_a_left_8']), ':',
         Paragraph(f"{'{:,}'.format(difference_weight)}", styles['narrow_a_right_8'])]
    ]

    total_table = Table(total_data, colWidths=[w * 15 / 100,
                                                 w * 15 / 100,
                                                 w * 44 / 100,
                                                 w * 13 / 100,
                                                 w * 3 / 100,
                                                 w * 10 / 100,
                                                 ])
    total_table.setStyle(TableStyle([
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (5, 0), (-1, 0), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        # ('GRID', (-2, 0), (-1, -1), 0.25, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('LINEABOVE', (5, 3), (-1, 3), 0.5, colors.black),
    ]))

    # Construir el documento
    elements = []
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=0.5, color="black", spaceBefore=3, spaceAfter=3))
    elements.append(transport_table)
    # elements.append(Spacer(1, 5))
    elements.append(HRFlowable(width="100%", thickness=0.5, color="black", spaceBefore=3, spaceAfter=3))
    elements.append(detail_header_table)
    elements.append(HRFlowable(width="100%", thickness=0.5, color="black", spaceBefore=0, spaceAfter=2))
    elements.append(detail_table)
    elements.append(Spacer(1, 10))
    elements.append(total_table)

    # Generar PDF
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        rightMargin=mr,
        leftMargin=ml,
        topMargin=mt,
        bottomMargin=mb,
        title=f"Picking {picking_obj.picking_number.zfill(4)}"
    )

    doc.build(elements)

    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = f'inline; filename="picking_{picking_obj.picking_number}.pdf"'
    response['Content-Disposition'] = 'inline; filename="somefilename.pdf"'
    response['Content-Disposition'] = 'attachment; filename="PICKING[{}].pdf"'.format(str(picking_obj.picking_number))
    response.write(buff.getvalue())
    buff.close()

    return response
