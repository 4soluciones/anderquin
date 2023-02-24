from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

from apps.hrm.models import Subsidiary, District, DocumentType
from apps.sales.models import Unit, Product, Supplier, SubsidiaryStore
from apps.comercial.models import Truck
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust


class Purchase(models.Model):
    STATUS_CHOICES = (('S', 'SIN ALMACEN'), ('A', 'EN ALMACEN'),)
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE)
    purchase_date = models.DateField('Fecha compra', null=True, blank=True)
    bill_number = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='S')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=15, default=0)

    def __str__(self):
        return self.id

    def multiplicate(self):
        return self.quantity * self.price_unit

    class Meta:
        verbose_name = 'Detalle compra'
        verbose_name_plural = 'Detalles de compra'


class Requirement_buys(models.Model):
    STATUS_CHOICES = (('1', 'PENDIENTE'), ('2', 'APROBADO'), ('3', 'ANULADO'), ('4', 'FINALIZADO'),)
    TYPE_CHOICES = (('M', 'MERCADERIA'), ('I', 'INSUMO'),)
    id = models.AutoField(primary_key=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='1', )
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='M', )
    creation_date = models.DateField('Fecha de solicitud', null=True, blank=True)
    number_scop = models.CharField('Numero de scop', max_length=45, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    invoice = models.CharField('Factura', max_length=45, null=True, blank=True)
    approval_date = models.DateField('Fecha de aprobación', null=True, blank=True)

    def __str__(self):
        str(self.id) + " - " + str(self.status)

    class Meta:
        verbose_name = 'Requerimiento'
        verbose_name_plural = 'Requerimientos'


class RequirementDetail_buys(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    requirement_buys = models.ForeignKey('Requirement_buys', on_delete=models.CASCADE, related_name='requirements_buys')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)

    def __str__(self):
        str(self.product.code) + " / " + str(self.requirement.id)

    def multiplicate(self):
        return self.quantity * self.price

    class Meta:
        verbose_name = 'Detalle requerimiento'
        verbose_name_plural = 'Detalles de requerimiento'


class RequirementBuysProgramming(models.Model):
    STATUS_CHOICES = (('P', 'PROGRAMADO'), ('F', 'FINALIZADO'),)
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='truck')
    date_programming = models.DateField('Fecha de solicitud', null=True, blank=True)
    number_scop = models.CharField('Numero de scop', max_length=45, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    # subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Programacion de Requerimiento GLP'
        verbose_name_plural = 'Programaciones de Requerimiento GLP'


class Programminginvoice(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('R', 'REGISTRADO'),)
    id = models.AutoField(primary_key=True)
    requirementBuysProgramming = models.ForeignKey(RequirementBuysProgramming, on_delete=models.SET_NULL, null=True,
                                                   blank=True)
    requirement_buys = models.ForeignKey(Requirement_buys, on_delete=models.SET_NULL, null=True, blank=True)
    date_arrive = models.DateField('Fecha de entrada', null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    guide = models.CharField('Numero Guia', max_length=45, null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    subsidiary_store = models.ForeignKey(SubsidiaryStore, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def calculate_total_quantity(self):
        response = Programminginvoice.objects.filter(requirement_buys_id=self.requirement_buys.id).values(
            'requirement_buys').annotate(totals=Sum('quantity'))
        # return response.count
        return response[0].get('totals')

    def calculate_total_programming_quantity(self):
        response = Programminginvoice.objects.filter(requirementBuysProgramming_id=self.requirementBuysProgramming.id).values(
            'requirementBuysProgramming').annotate(totals=Sum('quantity'))
        # return response.count
        return response[0].get('totals')

    class Meta:
        verbose_name = 'Factura GLP'
        verbose_name_plural = 'Facturas GLP'


class ProgrammingExpense(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('R', 'REGISTRADO'),)
    TYPE_CHOICES = (('C', 'COMBUSTILE'), ('F', 'FLETE'),)
    id = models.AutoField(primary_key=True)
    requirementBuysProgramming = models.ForeignKey(RequirementBuysProgramming, on_delete=models.SET_NULL, null=True,
                                                   blank=True)
    invoice = models.CharField('Factura', max_length=45, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    type = models.CharField('Estado', max_length=1, choices=TYPE_CHOICES, default='C', )
    date_invoice = models.DateField('Fecha de Facturacion', null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    noperation = models.CharField('Numero Guia', max_length=45, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Tanqueo'
        verbose_name_plural = 'Tanqueos'


class RateRoutes(models.Model):
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='trucks')
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,related_name='subsidiarys')
    def __str__(self):
        return str(self.id)
    class Meta:
        verbose_name = 'Ruta Tarifario'
        verbose_name_plural = 'Ruta Tarifarios'

