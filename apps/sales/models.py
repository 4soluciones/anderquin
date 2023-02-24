import decimal

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Min, Sum

from apps.comercial import apps
from apps.hrm.models import Subsidiary, District, DocumentType
from apps.accounting.models import Cash, CashFlow

from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust


# Create your models here.


class Unit(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=5, unique=True)
    description = models.CharField('Descripcion', max_length=50, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Unidad de medida'
        verbose_name_plural = 'Unidades de medida'


class ProductFamily(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Familia'
        verbose_name_plural = 'Familias'


class ProductBrand(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'


class ProductCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'


class ProductSubcategory(models.Model):
    id = models.AutoField(primary_key=True)
    product_category = models.ForeignKey('ProductCategory', on_delete=models.CASCADE)
    name = models.CharField('Nombre', max_length=45)
    is_enabled = models.BooleanField('Habilitado', default=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('product_category', 'name',)
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'


class SubsidiaryStore(models.Model):
    CATEGORY_CHOICES = (
        ('M', 'MERCADERIA'), ('I', 'INSUMO'), ('V', 'VENTA'), ('R', 'MANTENIMIENTO'), ('G', 'GLP'),
        ('O', 'OSINERGMIN'),)
    id = models.AutoField(primary_key=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField('Nombre', max_length=45)
    category = models.CharField('Categoria', max_length=1, choices=CATEGORY_CHOICES, default='M')

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('subsidiary', 'category',)
        verbose_name = 'Almacen de sucursal'
        verbose_name_plural = 'Almacenes de sucursal'


class Product(models.Model):
    VALVULE_CHOICES = (('N', 'NO ESPECIFICA'), ('P', 'PREMIUM'), ('R', 'ROSCA'), ('P', 'PRESION'),)
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=100, unique=True)
    observation = models.CharField('Observacion', max_length=50, null=True, blank=True)
    code = models.CharField('Codigo', max_length=45, null=True, blank=True)
    stock_min = models.IntegerField('Stock Minimno', default=0)
    stock_max = models.IntegerField('Stock Maximo', default=0)
    product_family = models.ForeignKey('ProductFamily', on_delete=models.CASCADE)
    product_brand = models.ForeignKey('ProductBrand', on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='product/',
                              default='pic_folder/None/no-img.jpg', blank=True)
    photo_thumbnail = ImageSpecField([Adjust(contrast=1.2, sharpness=1.1), ResizeToFill(
        100, 100)], source='photo', format='JPEG', options={'quality': 90})
    barcode = models.CharField('Codigo de barras', max_length=45, null=True, blank=True)
    valvule = models.CharField('Tipo de Valvula', max_length=1,
                               choices=VALVULE_CHOICES, default='N', )
    product_subcategory = models.ForeignKey('ProductSubcategory', on_delete=models.CASCADE)

    is_supply = models.BooleanField('Suministro', default=False)
    is_merchandise = models.BooleanField('Mercancia', default=False)
    is_epp = models.BooleanField('EPP', default=False)
    is_equipment = models.BooleanField('Equipo', default=False)
    is_machine = models.BooleanField('Maquina', default=False)
    is_purchased = models.BooleanField('Comprado', default=False)
    is_manufactured = models.BooleanField('Fabricado', default=False)
    is_imported = models.BooleanField('Importado', default=False)
    is_enabled = models.BooleanField('Habilitado', default=True)
    is_approved_by_osinergmin = models.BooleanField('Es aprobado por osinergmin', default=False)

    def __str__(self):
        return str(self.name) + " - " + str(self.code)

    def calculate_minimum_unit(self):
        response = ProductDetail.objects.filter(product__id=self.id).values('product__id').annotate(
            minimum=Min('quantity_minimum'))
        if response:
            return response[0].get('minimum')
        else:
            return 0

    def calculate_minimum_unit_id(self):
        response = self.productdetail_set.filter(quantity_minimum=self.calculate_minimum_unit()).first().unit.id
        return response

    def calculate_minimum_price_sale(self):
        response = self.productdetail_set.filter(quantity_minimum=self.calculate_minimum_unit()).first().price_sale
        return response

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'


class ProductDetail(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE)
    price_sale = models.DecimalField('Precio de Venta', max_digits=10, decimal_places=2, default=0)
    quantity_minimum = models.DecimalField('Cantidad Minima', max_digits=10, decimal_places=2, default=0)
    is_enabled = models.BooleanField('Habilitado', default=True)

    def __str__(self):
        return str(self.product.name) + " - " + str(self.unit.name)

    def get_price_sale_with_dot(self):
        return str(self.price_sale).replace(',', '.')

    def get_quantity_minimum_with_dot(self):
        return str(self.quantity_minimum).replace(',', '.')

    class Meta:
        unique_together = ('product', 'unit',)
        verbose_name = 'Presentacion'
        verbose_name_plural = 'Presentaciones'


class ProductStore(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey('Product', verbose_name='Producto', on_delete=models.CASCADE)
    subsidiary_store = models.ForeignKey(
        'SubsidiaryStore', verbose_name='Almacen sucursal', on_delete=models.CASCADE, related_name='stores')
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.product.name

    def get_stock_with_dot(self):
        return str(self.stock).replace(',', '.')

    def conversion_mml_g_stock(self):
        paint_converter = ProductStore.objects.filter(product__product_family__id=4)
        if paint_converter.count() > 0:
            response = float(self.stock) / float(3785.41)
        return response

    class Meta:
        unique_together = ('product', 'subsidiary_store',)
        verbose_name = 'Almacen de producto (Lote)'
        verbose_name_plural = 'Almacenes de producto (Lotes)'


class Supplier(models.Model):
    SECTOR_CHOICES = (('N', 'NO ESPECIFICA'),
                      ('L', 'LLANTAS'),
                      ('P', 'PINTURA'),
                      ('PR', 'PRECINTO'),
                      ('R', 'REPUESTO'),
                      ('C', 'COMBUSTIBLE'),
                      ('G', 'GLP'),
                      ('S', 'SEGUROS'),
                      ('SU', 'SUNAT'),
                      ('LU', 'LUBRICANTES'),
                      ('LA', 'LAVADO'),
                      ('M', 'MANTENIMIENTO'),
                      ('PE', 'PEAJES'),
                      ('O', 'OTROS'),)
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=200, unique=True)
    business_name = models.CharField('Razon social', max_length=45, null=True, blank=True)
    ruc = models.CharField('Ruc de la empresa', max_length=11, null=True, blank=True)
    phone = models.CharField('Telefono de la empresa', max_length=45, null=True, blank=True)
    address = models.CharField('Dirección de la empresa', max_length=200, null=True, blank=True)
    email = models.EmailField('Email de la empresa', max_length=50, null=True, blank=True)
    contact_names = models.CharField('Nombres del contacto', max_length=45, null=True, blank=True)
    contact_surnames = models.CharField(
        'Apellidos del contacto', max_length=90, null=True, blank=True)
    contact_document_number = models.CharField(
        'Numero de documento del contacto', max_length=15, null=True, blank=True)
    contact_phone = models.CharField('Telefono del contacto', max_length=45, null=True, blank=True)
    is_enabled = models.BooleanField('Habilitado', default=True)
    sector = models.CharField('Tipo de Rubro', max_length=2, choices=SECTOR_CHOICES, default='N', )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'


class ProductSupplier(models.Model):
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    price_purchase = models.DecimalField(
        'Precio de Compra', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.supplier.name) + " - " + str(self.product.name)

    class Meta:
        unique_together = ('supplier', 'product',)
        verbose_name = 'Precio segun proveedor'
        verbose_name_plural = 'Precios segun proveedor'


class Requirement(models.Model):
    STATUS_CHOICES = (('1', 'PENDIENTE'), ('2', 'APROBADO'), ('3', 'LIQUIDADO'),
                      ('4', 'OBSERVADO'), ('5', 'EN PROCESO'), ('6', 'ANULADO'),)
    TYPE_CHOICES = (('M', 'MERCADERIA'), ('I', 'INSUMO'),)
    id = models.AutoField(primary_key=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='1', )
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='M', )
    creation_date = models.DateField('Fecha de solicitud', null=True, blank=True)
    approval_date = models.DateField('Fecha de aprobación', null=True, blank=True)
    delivery_date = models.DateField('Fecha de entrega', null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id) + " - " + str(self.status)

    class Meta:
        verbose_name = 'Requerimiento'
        verbose_name_plural = 'Requerimientos'


class RequirementDetail(models.Model):
    CONDITION_CHOICES = (('P', 'PENDIENTE'), ('S', 'SOLICITADO'), ('A', 'ANULADO'),)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    requirement = models.ForeignKey('Requirement', on_delete=models.CASCADE)
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE)
    quantity = models.IntegerField('Cantidad', default=0)
    commentary = models.CharField(max_length=200, null=True, blank=True)
    condition = models.CharField('Estado', max_length=1, choices=CONDITION_CHOICES, default='P', )

    def __str__(self):
        return str(self.product.code) + " / " + str(self.requirement.id)

    class Meta:
        verbose_name = 'Detalle requerimiento'
        verbose_name_plural = 'Detalles de requerimiento'


class Client(models.Model):
    id = models.AutoField(primary_key=True)
    names = models.CharField(max_length=45, null=True, blank=True, unique=True)
    phone = models.CharField('Telefono', max_length=9, null=True, blank=True)
    email = models.EmailField('Correo electronico', max_length=50, null=True, blank=True)

    def __str__(self):
        return self.names

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class ClientType(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, )
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    document_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return str(self.document_number)

    class Meta:
        unique_together = ('document_number', 'document_type',)
        verbose_name = 'Tipo de Cliente'
        verbose_name_plural = 'Tipos de Clientes'


class ClientAddress(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, )
    address = models.CharField('Dirección', max_length=200, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.CharField('Referencia', max_length=400, null=True, blank=True)

    def __str__(self):
        return str(self.address)

    class Meta:
        verbose_name = 'Direccion de Cliente'
        verbose_name_plural = 'Direcciones del Clientes'


class ClientAssociate(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, )
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.client.id)

    class Meta:
        verbose_name = 'Cliente Asociado'
        verbose_name_plural = 'Clientes Asociados'


class Order(models.Model):
    TYPE_CHOICES = (('V', 'VENTA'), ('C', 'COMPRA'), ('R', 'REPARTO'), ('E', 'ELECTRONICO'),)
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('C', 'COMPLETADO'), ('A', 'ANULADO'),)
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='C', )
    supplier = models.ForeignKey('Supplier', verbose_name='Proveedor',
                                 on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary_store = models.ForeignKey(
        'SubsidiaryStore', verbose_name='Almacen Sucursal', on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey('Client', verbose_name='Cliente',
                               on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    requirement = models.ManyToManyField('Requirement', related_name='requirements', blank=True)
    operation_code = models.CharField(
        verbose_name='Codigo de operación', max_length=45, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    create_at = models.DateTimeField(null=True, blank=True)
    update_at = models.DateTimeField(auto_now=True)
    total = models.DecimalField('Total', max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField('Descuento', max_digits=10, decimal_places=2, default=0)
    distribution_mobil = models.ForeignKey('comercial.DistributionMobil', on_delete=models.SET_NULL, null=True,
                                           blank=True)
    correlative_sale = models.CharField(
        verbose_name='Correlativo de Ventas', max_length=45, null=True, blank=True)
    truck = models.ForeignKey('comercial.Truck', on_delete=models.SET_NULL, null=True,
                              blank=True)
    is_review = models.BooleanField('Revisado', default=False)
    subsidiary = models.ForeignKey('hrm.Subsidiary', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    def total_repay_loan(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            response = response + d.repay_loan()
        return response

    def total_repay_loan_with_vouchers(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            response = response + d.repay_loan_with_vouchers()
        return response

    def total_return_loan(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            response = response + d.return_loan()
        return response

    def total_remaining_repay_loan(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            if d.unit.name == 'G' or d.unit.name == 'GBC':
                response = response + (d.multiply() - d.repay_loan())
        return response

    def total_remaining_repay_loan_ball(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            if d.unit.name == 'B':
                response = response + (d.multiply() - d.repay_loan_ball())
        return response

    def total_remaining_return_loan(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            if d.unit.name == 'B':
                response = response + (d.quantity_sold - d.return_loan())
        return response

    def total_ball_changes(self):
        response = 0
        order_detail_set = OrderDetail.objects.filter(order__id=self.pk, order__type__in=['R', 'V'])
        for d in order_detail_set:
            response = response + d.ball_changes()
        return response

    def total_cash_flow_spending(self):
        response = 0
        cash_flow_pay_spending_set = CashFlow.objects.filter(order__id=self.pk, type='S')
        for cf in cash_flow_pay_spending_set:
            response = response + cf.total
        return response

    def count_sales_details_b(self):
        return len(self.sales_details_b())

    def sales_details_b(self):
        _details = []
        for d in self.orderdetail_set.filter(unit__name='B'):
            if not d.validate_debt():
                _details.append(d)
        return _details

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Ordenes'


class OrderDetail(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('E', 'EN PROCESO'),
                      ('C', 'COMPRADO'), ('V', 'VENDIDO'), ('A', 'ANULADO'),)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity_sold = models.DecimalField('Cantidad vendida', max_digits=10, decimal_places=2, default=0)
    quantity_purchased = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=2, default=0)
    quantity_requested = models.DecimalField('Cantidad solicitada', max_digits=10, decimal_places=2, default=0)
    price_unit = models.DecimalField('Precio unitario', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE)
    commentary = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )

    def __str__(self):
        return str(self.pk)

    def multiply(self):
        return self.quantity_sold * self.price_unit

    def return_loan(self):
        response = 0
        loan_payment_set = LoanPayment.objects.filter(order_detail=self.pk).values(
            'order_detail').annotate(totals=Sum('quantity'))
        if loan_payment_set.count() > 0:
            response = loan_payment_set[0].get('totals')
        return response

    def repay_loan(self):
        response = 0
        loan_payment_set = LoanPayment.objects.filter(order_detail=self.pk, quantity=0).values(
            'order_detail').annotate(totals=Sum('price'))
        if loan_payment_set.count() > 0:
            response = loan_payment_set[0].get('totals')
        return response

    def repay_loan_ball(self):
        response = 0
        loan_payment_set = LoanPayment.objects.filter(order_detail=self.pk)
        for lp in loan_payment_set:
            response = response + (lp.quantity * (lp.price + lp.discount))
        return response

    def ball_changes(self):
        response = 0
        ball_change_set = BallChange.objects.filter(order_detail=self.pk).values(
            'order_detail').annotate(totals=Sum('quantity'))
        if ball_change_set.count() > 0:
            response = ball_change_set[0].get('totals')
        return response

    def repay_loan_with_vouchers(self):
        response = 0
        loan_payment_set = LoanPayment.objects.filter(order_detail=self.pk)
        for lp in loan_payment_set:
            if lp.price > 0:
                transaction_payment = lp.transactionpayment_set.first()
                if transaction_payment and transaction_payment.type == 'F':
                    response = response + transaction_payment.number_of_vouchers
        return response

    def multiply_return_loan(self):
        return self.return_loan() * self.price_unit

    def validate_debt(self):
        response = False
        if self.quantity_sold == self.return_loan():
            response = True
        return response

    class Meta:
        verbose_name = 'Detalle orden'
        verbose_name_plural = 'Detalles de orden'


class TransactionPayment(models.Model):
    TYPE_CHOICES = (('E', 'Efectivo'), ('D', 'Deposito'), ('F', 'FISE'))
    id = models.AutoField(primary_key=True)
    payment = models.DecimalField('Pago', max_digits=10, decimal_places=2, default=0)
    type = models.CharField('Tipo de pago', max_length=1, choices=TYPE_CHOICES, default='E', )
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    operation_code = models.CharField(
        verbose_name='Codigo de operación', max_length=45, null=True, blank=True)
    number_of_vouchers = models.DecimalField('Vales FISE', max_digits=10, decimal_places=2, default=0)
    loan_payment = models.ForeignKey('LoanPayment', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.order.id) + " - " + str(self.type) + " - " + str(self.payment)

    def get_cash_flow(self):
        response = None
        if self.type == 'D':
            cash_flow_set = CashFlow.objects.filter(type='D',
                                                    total=self.payment,
                                                    order=self.loan_payment.order_detail.order,
                                                    operation_code=self.operation_code)
            if cash_flow_set:
                response = cash_flow_set.last()
        return response

    class Meta:
        verbose_name = 'Transacción de pago'
        verbose_name_plural = 'Transacciones de pago'


class Kardex(models.Model):
    OPERATION_CHOICES = (('E', 'Entrada'), ('S', 'Salida'), ('C', 'Inventario inicial'),)
    id = models.AutoField(primary_key=True)
    operation = models.CharField('Tipo de operación', max_length=1,
                                 choices=OPERATION_CHOICES, default='C', )
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=15, default=0)
    price_total = models.DecimalField('Precio total', max_digits=30, decimal_places=15, default=0)
    remaining_quantity = models.DecimalField('Cantidad restante', max_digits=10, decimal_places=2, default=0)
    remaining_price = models.DecimalField(
        'Precio restante', max_digits=30, decimal_places=15, default=0)
    remaining_price_total = models.DecimalField(
        'Precio total restante', max_digits=30, decimal_places=15, default=0)
    product_store = models.ForeignKey(
        'ProductStore', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_detail = models.ForeignKey('buys.PurchaseDetail', on_delete=models.SET_NULL, null=True, blank=True)
    guide_detail = models.ForeignKey('comercial.GuideDetail', on_delete=models.SET_NULL, null=True, blank=True)
    requirement_detail = models.ForeignKey('buys.RequirementDetail_buys', on_delete=models.SET_NULL, null=True,
                                           blank=True)
    programming_invoice = models.ForeignKey('buys.Programminginvoice', on_delete=models.SET_NULL, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    manufacture_detail = models.ForeignKey('ManufactureDetail', on_delete=models.SET_NULL, null=True, blank=True)
    manufacture_recipe = models.ForeignKey('ManufactureRecipe', on_delete=models.SET_NULL, null=True, blank=True)
    distribution_detail = models.ForeignKey('comercial.DistributionDetail', on_delete=models.SET_NULL, null=True,
                                            blank=True)
    loan_payment = models.ForeignKey('LoanPayment', on_delete=models.SET_NULL, null=True, blank=True)
    ball_change = models.ForeignKey('BallChange', on_delete=models.SET_NULL, null=True, blank=True)
    advance_detail = models.ForeignKey('comercial.ClientAdvancementDetail', on_delete=models.SET_NULL, null=True,
                                       blank=True)

    def conversion_mml_g(self):
        paint_converter = ProductStore.objects.filter(product__product_family__id=4)
        if paint_converter.count() > 0:
            response = float(self.quantity) / float(3785.41)
        return response

    def conversion_mml_g_remainig(self):
        paint_converter = ProductStore.objects.filter(product__product_family__id=4)
        if paint_converter.count() > 0:
            response = float(self.remaining_quantity) / float(3785.41)
        return response

    class Meta:
        verbose_name = 'Registro de Kardex'
        verbose_name_plural = 'Registros de Kardex'


class OrderBill(models.Model):
    STATUS_CHOICES = (('E', 'Emitido'), ('A', 'Anulado'),)
    TYPE_CHOICES = (('1', 'Factura'), ('2', 'Boleta'),)
    IS_DEMO_CHOICES = (('D', 'Demo'), ('P', 'Produccion'),)
    order = models.OneToOneField('Order', on_delete=models.CASCADE, primary_key=True)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    type = models.CharField('Tipo de Comprobante', max_length=2, choices=TYPE_CHOICES)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0)
    sunat_status = models.CharField('Sunat Status', max_length=5, null=True, blank=True)
    sunat_description = models.CharField('Sunat descripcion', max_length=200, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    sunat_enlace_pdf = models.CharField('Sunat Enlace Pdf', max_length=200, null=True, blank=True)
    # total = models.DecimalField('Monto Total', max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    code_qr = models.CharField('Codigo QR', max_length=500, null=True, blank=True)
    code_hash = models.CharField('Codigo Hash', max_length=500, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES)
    is_demo = models.CharField('Demo', max_length=1, choices=IS_DEMO_CHOICES, null=True, blank=True)

    def __str__(self):
        return str(self.order.id)

    class Meta:
        verbose_name = 'Registro de Comprobante'
        verbose_name_plural = 'Registros de Comprobantes'


class ProductRecipe(models.Model):
    product_input = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='inputs')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='recipes')
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE)
    price = models.DecimalField('Precio Unitario', max_digits=10, decimal_places=2, default=0)

    # total = models.DecimalField('Precio Total', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.pk)

    def get_price_with_dot(self):
        return str(self.price).replace(',', '.')

    def get_quantity_with_dot(self):
        return str(self.quantity).replace(',', '.')

    class Meta:
        verbose_name = 'Registro de Receta'
        verbose_name_plural = 'Registros de Recetas'


class Manufacture(models.Model):
    code = models.CharField('Numero de comprobante', max_length=45, null=True, blank=True)
    total = models.DecimalField('Precio Total', max_digits=10, decimal_places=2, default=0)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Registro de Orden Fabricacion'
        verbose_name_plural = 'Registros de Ordenes de Fabricaciones'


class ManufactureAction(models.Model):
    STATUS_CHOICES = (('1', 'PENDIENTE'), ('2', 'APROBADO'), ('3', 'EN PRODUCCION'),
                      ('4', 'FINALIZADO'), ('5', 'ANULADO'),)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    manufacture = models.ForeignKey('Manufacture', on_delete=models.CASCADE)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='1', )

    def __str__(self):
        return str(self.id)


class ManufactureDetail(models.Model):
    manufacture = models.ForeignKey('Manufacture', on_delete=models.CASCADE)
    product_manufacture = models.ForeignKey('Product', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ('manufacture', 'product_manufacture')
        verbose_name = 'Registro de Detalles de Fabricacion'
        verbose_name_plural = 'Registros de Detalle de Fabricaciones'


class ManufactureRecipe(models.Model):
    manufacture_detail = models.ForeignKey('ManufactureDetail', on_delete=models.CASCADE)
    product_input = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.id)


class LoanPayment(models.Model):
    TYPE_CHOICES = (('V', 'Venta'), ('C', 'Compra'),)
    id = models.AutoField(primary_key=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    discount = models.DecimalField('Descuento', max_digits=30, decimal_places=15, default=0)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    type = models.CharField('Tipo de Operacion', max_length=1, choices=TYPE_CHOICES, default='V', )
    purchase = models.ForeignKey('buys.Purchase', on_delete=models.SET_NULL, null=True, blank=True)
    operation_date = models.DateField('Fecha de operacion', null=True, blank=True)
    distribution_mobil = models.ForeignKey('comercial.DistributionMobil', on_delete=models.SET_NULL, null=True,
                                           blank=True)
    requirement_detail_buys = models.ForeignKey('buys.RequirementDetail_buys', on_delete=models.SET_NULL, null=True,
                                                blank=True)
    is_check = models.BooleanField('check', default=False)

    def __str__(self):
        return str(self.id)

    def get_cash_flow(self):
        cash_flow_set = CashFlow.objects.filter(total=self.price,
                                                requirement_buys=self.requirement_detail_buys.requirement_buys)
        if cash_flow_set.exists():
            return cash_flow_set.first()
        return None


class BallChange(models.Model):
    STATUS_CHOICES = (
        ('1', 'Corrosión excesiva'), ('2', 'Abolladuras'), ('3', 'Válvula pintada o con fugas de gas'), ('4', 'Otro'))
    id = models.AutoField(primary_key=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='4', )
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    observation = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class LoanAccount(models.Model):
    OPERATION_CHOICES = (('L', 'Prestado'), ('P', 'Pagado'),)
    id = models.AutoField(primary_key=True)
    operation = models.CharField('Tipo de operación', max_length=1,
                                 choices=OPERATION_CHOICES, default='L', )
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=15, default=0)
    price_total = models.DecimalField('Precio total', max_digits=30, decimal_places=15, default=0)
    remaining_quantity = models.DecimalField('Cantidad restante', max_digits=10, decimal_places=2, default=0)
    remaining_price = models.DecimalField(
        'Precio restante', max_digits=30, decimal_places=15, default=0)
    remaining_price_total = models.DecimalField(
        'Precio total restante', max_digits=30, decimal_places=15, default=0)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey('Client', verbose_name='Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    loan_payment = models.ForeignKey('LoanPayment', on_delete=models.SET_NULL, null=True, blank=True)

    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Registro de Prestamo'
        verbose_name_plural = 'Registros de Prestamo'

    def __str__(self):
        return str(self.id)


class Perceptron(models.Model):
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    client = models.ForeignKey('Client', verbose_name='Cliente',
                               on_delete=models.SET_NULL, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    total_received = models.DecimalField('Total Percibido', max_digits=10, decimal_places=2, default=0)
    total_charged = models.DecimalField('Total Cobrado con Percepcion', max_digits=10, decimal_places=2, default=0)
    observation = models.CharField('Observacion', max_length=50, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class PerceptronDetail(models.Model):
    order_bill = models.ForeignKey('OrderBill', on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    total_no_perceptron = models.DecimalField('Total Cobrado sin Percepcion', max_digits=10, decimal_places=2,
                                              default=0)
    total_perceptron_received = models.DecimalField('Total Recibido', max_digits=10, decimal_places=2, default=0)
    charged_date = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    total_perceptron = models.DecimalField('Total Cobrado con Percepcion', max_digits=10, decimal_places=2, default=0)
    sunat_status = models.CharField('Sunat Status', max_length=5, null=True, blank=True)
    sunat_description = models.CharField('Sunat descripcion', max_length=200, null=True, blank=True)
    sunat_enlace_pdf = models.CharField('Sunat Enlace Pdf', max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.id)
