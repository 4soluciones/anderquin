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
from django.template import loader
from datetime import datetime
import io
import pdfkit


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
