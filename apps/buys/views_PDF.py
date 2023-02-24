import reportlab
from reportlab.lib.colors import black, white, gray, red, green, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, tables
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import Table, Flowable
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.rl_settings import defaultPageSize
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color, black, blue, red, pink
from anderquin import settings
from django.http import HttpResponse
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from .views import get_kardex_dictionary
from .models import Requirement_buys, RequirementDetail_buys
from django.template import loader
from datetime import datetime
import io
import pdfkit


def kardex_glp_pdf(request, date_initial, date_final):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        html = get_kardex_dictionary(subsidiary_obj, is_pdf=True, start_date=date_initial, end_date=date_final)
        options = {
            'page-size': 'A3',
            'orientation': 'Landscape',
            'encoding': "UTF-8",
        }
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

        pdf = pdfkit.from_string(html, False, options, configuration=config)
        response = HttpResponse(pdf, content_type='application/pdf')
        # response['Content-Disposition'] = 'attachment;filename="kardex_pdf.pdf"'
        return response


def print_requirement(request, pk=None):
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    requirement_buy_obj = Requirement_buys.objects.get(id=int(pk))
    requirement_detail_buy_obj = requirement_buy_obj.requirements_buys.first()
    buff = io.BytesIO()

    ml = 1.0 * cm
    mr = 3.0 * cm
    ms = 3.0 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title="Orden de requerimiento - [{}-{}]".format(requirement_buy_obj.id,
                                                                            requirement_buy_obj.number_scop),
                            )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, leading=13, fontName='Newgot', fontSize=12))
    styles.add(
        ParagraphStyle(name='header2', alignment=TA_CENTER, leading=13, fontName='Helvetica', fontSize=8))
    styles.add(
        ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))

    tpl_title = ('ORDEN COMPRA PLUSPETROL', '')
    tpl_company = ('Nombre Empresa', requirement_buy_obj.subsidiary.business_name)
    tpl_ruc = ('Número RUC', requirement_buy_obj.subsidiary.ruc)
    tpl_dgh = ('Número DGH', requirement_buy_obj.subsidiary.dgh)
    tpl_date = ('Fecha Orden de Compra', requirement_buy_obj.creation_date)
    tpl_product = ('Tipo de Producto', '{} - G'.format(requirement_detail_buy_obj.product.name))
    tpl_quantity = (
    'Cantidad de Glp', '{} {}'.format(str(requirement_detail_buy_obj.quantity), requirement_detail_buy_obj.unit.name))
    tpl_point = ('Punto de Entrega', 'Pisco')
    tpl_scop = ('Nº Scop', requirement_buy_obj.number_scop)
    tpl_buyer = ('Nombre comprador', requirement_buy_obj.subsidiary.legal_representative_name)
    tpl_dni = ('Número de DNI', requirement_buy_obj.subsidiary.legal_representative_dni)

    t = Table([tpl_title] + [tpl_company] + [tpl_ruc] + [tpl_dgh] + [tpl_date] + [tpl_product] + [tpl_quantity] + [
        tpl_point] + [tpl_scop] + [tpl_buyer] + [tpl_dni])
    # wave-transparent-background
    t.setStyle(TableStyle(
        [
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 5), (1, 6), 'Helvetica-Bold'),
            ('FONTNAME', (1, 8), (1, 8), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 30),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 8), (1, 8), 10),
        ]
    ))

    Story = []

    Story.append(Spacer(40, 100))
    Story.append(t)
    Story.append(Spacer(1, 10))
    Story.append(OutputPrintRequirement())
    Story.append(Spacer(1, 1))
    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="Orden_de_requerimiento_[{}-{}].pdf"'.format(
        requirement_buy_obj.id, requirement_buy_obj.number_scop)
    doc.build(Story)
    r.write(buff.getvalue())
    buff.close()
    return r


class OutputPrintRequirement(Flowable):
    def __init__(self, width=200, height=100):
        self.width = width
        self.height = height

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFillColor(white)
        glp = "apps/dishes/static/assets/avatar/VJglp20.png"
        wave = "apps/dishes/static/assets/avatar/wave-transparent-background.png"
        canvas.drawImage(glp, 0 - 0, 520, mask='auto', width=150 / 2.2, height=150 / 2.2)
        canvas.drawImage(wave, 0 - 50, 0 - 220, mask='auto', width=980 / 1.5, height=128 / 1.5)
        canvas.line(80 - 0, 17, 80 - 0 + 150, 17)
        canvas.line(300, 17, 300 + 150, 17)

        canvas.setFillColor(black)
        canvas.setFont('Square', 28)
        canvas.drawString(0 + 120, 520 + 35, 'VICTORIA JUAN GAS S.A.C.')
        canvas.setFont('Square', 15)
        canvas.drawString(0 + 195, 500 + 30, 'R.U.C. 20450509125')
        canvas.setLineWidth(2)
        canvas.line(0, 515, 0 + 520, 515)
        canvas.setLineWidth(1)
        canvas.line(0, 511, 0 + 520, 511)

        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(80 + 5, 7, 'Firma')
        canvas.drawString(300 + 5, 7, 'Aprobado')
        canvas.setFillColor(white)
        canvas.setFont('Square', 14)
        canvas.drawString(0 + 320, 0 - 185, 'CARRETERA: SICUANI - JULIACA KM. 1113 -')
        canvas.drawString(0 + 430, 0 - 200, 'SICUANI - CUSCO')
        canvas.restoreState()
