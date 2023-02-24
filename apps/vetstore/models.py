from django.db import models
from django.contrib.auth.models import User
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust


# Create your models here.
class Role(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre', unique=True)
    code = models.CharField(max_length=3, verbose_name='Codigo', null=True, blank=True)

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'


class Schedule(models.Model):
    name = models.CharField(max_length=100, verbose_name='Desc. Corta', unique=True)
    tolerance = models.IntegerField(default=15, verbose_name='Tolerancia', null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación', null=True, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'


class Duration(models.Model):
    DAY_CHOICES = (('Lu', 'Lunes'), ('Ma', 'Martes'), ('Mi', 'Miercoles'),
                   ('Ju', 'Jueves'), ('Vi', 'Viernes'), ('Sa', 'Sabado'), ('Do', 'Domingo'),)
    schedule = models.ForeignKey(Schedule, verbose_name='Horario',
                                 related_name='durations', on_delete=models.CASCADE)
    day_week = models.CharField(max_length=2, verbose_name='Día de la semana', choices=DAY_CHOICES)
    start_working_day = models.TimeField(
        verbose_name='Inicio jornada laboral', blank=True, null=True)
    end_working_day = models.TimeField(
        verbose_name='Finalización jornada laboral', blank=True, null=True)
    start_time = models.TimeField(verbose_name='Hora de entrada', blank=True, null=True)
    end_time = models.TimeField(verbose_name='Hora de finalización', blank=True, null=True)
    snack_start_time = models.TimeField(
        verbose_name='Hora de inicio de merienda', blank=True, null=True)
    snack_end_time = models.TimeField(
        verbose_name='Hora de finalización de merienda', blank=True, null=True)

    def __unicode__(self):
        return unicode(self.day_week)

    def __str__(self):
        return self.day_week

    class Meta:
        verbose_name = 'Duracion'
        verbose_name_plural = 'Duraciones'


class BranchOffice(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre', unique=True)
    address = models.CharField(max_length=100, verbose_name='Dirección', null=True, blank=True)
    phone = models.CharField(max_length=50, verbose_name='Teléfono', blank=True)
    image = models.ImageField(upload_to='branch_office',
                              verbose_name='Imágen logo', blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'


class Employee(models.Model):
    STATUS_CHOICES = (('A', 'Activo'), ('I', 'Inactivo'),)
    user = models.OneToOneField(User, primary_key=True,
                                verbose_name='Usuario', on_delete=models.CASCADE)
    status = models.CharField(max_length=1, verbose_name='Estado',
                              choices=STATUS_CHOICES, default='A', )
    role = models.ManyToManyField(Role, verbose_name='Rol')
    schedule = models.ForeignKey(Schedule, verbose_name='Horario',
                                 blank=True, null=True, on_delete=models.CASCADE)
    branch_office = models.ForeignKey(
        BranchOffice, verbose_name='Sucursal', blank=True, null=True, on_delete=models.CASCADE)
    code = models.IntegerField(verbose_name='Id usuario', null=True, blank=True)

    def __unicode__(self):
        return unicode(self.user)

    def __str__(self):
        return self.user.first_name

    def get_branch_office(self):
        return self.branch_office.name

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'


class Attendance(models.Model):
    TYPE_CHOICES = (('A', 'Asistio'), ('F', 'Falto'), ('N', 'No justifico'),
                    ('P', 'Permiso'), ('J', 'Justifico'),)
    employee = models.ForeignKey(Employee, verbose_name='Empleado', on_delete=models.CASCADE)
    type = models.CharField(max_length=1, verbose_name='Tipo', choices=TYPE_CHOICES, default='A')
    comment = models.TextField(max_length=2000, verbose_name='Descripción', blank=True, null=True)
    date_assigned = models.DateField(verbose_name='Fecha asignada', null=True, blank=True)
    entry_time = models.TimeField(verbose_name='Hora de entrada', blank=True, null=True)
    departure_time = models.TimeField(verbose_name='Hora de salida', blank=True, null=True)
    hours_worked = models.TimeField(verbose_name='Horas trabajadas', blank=True, null=True)
    minutes_late = models.IntegerField(
        default=0, verbose_name='Minutos tarde', null=True, blank=True)
    minutes_early = models.IntegerField(
        default=0, verbose_name='Minutos temprano', null=True, blank=True)
    minutes_delay = models.IntegerField(
        default=0, verbose_name='Minutos retraso', null=True, blank=True)
    minutes_extra = models.IntegerField(
        default=0, verbose_name='Minutos extra', null=True, blank=True)
    update_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __unicode__(self):
        return unicode(self.employee)

    def __str__(self):
        return self.employee.user.first_name

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

    @property
    def weekday(self):

        switcher = {
            0: "Lu",
            1: "Ma",
            2: "Mi",
            3: "Ju",
            4: "Vi",
            5: "Sa",
            6: "Do"
        }
        return switcher.get(self.date_assigned.weekday(), 7)


class AttendanceDetail(models.Model):
    STATUS_CHOICES = (('E', 'Temprano'), ('O', 'A tiempo'), ('L', 'Tarde'),)
    status = models.CharField(max_length=1, verbose_name='Tipo',
                              choices=STATUS_CHOICES, default='O')
    attendance = models.ForeignKey(
        Attendance, verbose_name='Asistencia', related_name='attendances', on_delete=models.CASCADE)
    registered_time = models.TimeField(verbose_name='Hora de registrada', blank=True, null=True)

    def __unicode__(self):
        return self.registered_time

    def __str__(self):
        return self.registered_time

    class Meta:
        verbose_name = 'Detalle de asistencia'
        verbose_name_plural = 'Detalle de asistencias'


class Customer(models.Model):
    STATUS_CHOICES = (('A', 'Activo'), ('I', 'Inactivo'),)
    TYPE_CHOICES = (('N', 'Normal'), ('P', 'Pase'), ('M', 'Mayor'),)
    user = models.OneToOneField(User, primary_key=True,
                                verbose_name='Usuario', on_delete=models.CASCADE)
    status = models.CharField(max_length=1, verbose_name='Estado',
                              choices=STATUS_CHOICES, default='A', )
    type = models.CharField(max_length=1, verbose_name='Tipo', choices=TYPE_CHOICES, default='N', )

    def __unicode__(self):
        return unicode(self.user)

    def __str__(self):
        return self.user.first_name

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre', unique=True)
    comment = models.TextField(max_length=2000, verbose_name='Descripción', blank=True, null=True)
    parent = models.ForeignKey('Category', verbose_name='Categoría padre',
                               blank=True, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'


class Brand(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre', unique=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'


class Product(models.Model):
    STATUS_CHOICES = (('A', 'Con stock'), ('I', 'Inactivo'), ('S', 'Sin stock'),)
    name = models.CharField(max_length=100, verbose_name='Nombre', unique=True)
    label = models.CharField(max_length=200, verbose_name='Etiqueta', null=True, blank=True)
    comment = models.TextField(max_length=2000, verbose_name='Descripción', blank=True, null=True)
    barcode = models.TextField(max_length=100, verbose_name='BarCode', unique=True)
    factory_barcode = models.TextField(
        max_length=100, verbose_name='Código de barra de fábrica', blank=True, null=True)
    sale_price = models.DecimalField(
        default=0, decimal_places=2, max_digits=10, verbose_name='Precio de venta', null=True, blank=True)
    pass_price = models.DecimalField(
        default=0, decimal_places=2, max_digits=10, verbose_name='Precio de pase', null=True, blank=True)
    discount_price = models.DecimalField(
        default=0, decimal_places=2, max_digits=10, verbose_name='Precio de rebaja', null=True, blank=True)
    starting_inventory = models.IntegerField(
        default=0, verbose_name='Inventario inicial', null=True, blank=True)
    purchased_inventory = models.IntegerField(
        default=0, verbose_name='Inventario comprado', null=True, blank=True)
    sold_inventory = models.IntegerField(
        default=0, verbose_name='Inventario vendido', null=True, blank=True)
    returned_purchased_inventory = models.IntegerField(
        default=0, verbose_name='Inventario comprado devuelto', null=True, blank=True)
    returned_sold_inventory = models.IntegerField(
        default=0, verbose_name='Inventario vendido devuelto', null=True, blank=True)
    current_inventory = models.IntegerField(
        default=0, verbose_name='Inventario a la mano', null=True, blank=True)
    minimum_inventory = models.IntegerField(
        default=0, verbose_name='Inventario mínimo', null=True, blank=True)
    status = models.CharField(max_length=1, verbose_name='Estado',
                              choices=STATUS_CHOICES, default='A', )
    brand = models.ForeignKey(Brand, verbose_name='Marca',
                              related_name='brands', null=True, blank=True, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, verbose_name='Categoría',
                                 null=True, blank=True, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product', default='product/none/product.png',
                              verbose_name='Imágen', blank=True, null=True)
    image_thumbnail = ImageSpecField(source='image',
                                     processors=[ResizeToFill(300, 300)],
                                     format='JPEG',
                                     options={'quality': 80})
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'


class Wholesale(models.Model):
    product = models.ForeignKey(Product, verbose_name='Producto', on_delete=models.CASCADE)
    price = models.DecimalField(default=0, decimal_places=2, max_digits=10,
                                verbose_name='Precio al por mayor', null=True, blank=True)
    quantity = models.IntegerField(
        default=0, verbose_name='Cantidad al por mayor', null=True, blank=True)

    def __unicode__(self):
        return self.product.name

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = 'Venta al por mayor'
        verbose_name_plural = 'Ventas al por mayor'


class Supplier(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre', unique=True)
    cellphone = models.CharField(
        max_length=50, verbose_name='Teléfono Móvil', null=True, blank=True)
    contact = models.CharField(max_length=200, verbose_name='Contacto', null=True, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'


class Purchase(models.Model):
    TYPE_CHOICES = (('F', 'Factura'), ('B', 'Boleta'),)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name='Empleado',
                                 null=True, blank=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=1, verbose_name='Tipo', choices=TYPE_CHOICES)
    subtotal = models.DecimalField(
        max_digits=10, verbose_name='Subtotal', decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, verbose_name='Igv', decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, verbose_name='Total', decimal_places=2, default=0)
    operation_number = models.CharField(
        max_length=100, verbose_name='Número de operación', null=True, blank=True)
    request_date = models.DateTimeField(verbose_name='Fecha de solicitud', null=True, blank=True)
    receipt_date = models.DateTimeField(verbose_name='Fecha de recepción', null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación', null=True, blank=True)
    branch_office = models.ForeignKey(
        BranchOffice, verbose_name='Sucursal', blank=True, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.operation_number

    def __str__(self):
        return self.operation_number

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    @property
    def total_gain(self):
        total = 0
        for detail in self.detail_purchases.all():
            total += detail.gain
        return total


class Sales(models.Model):
    STATUS_CHOICES = (('A', 'Aprobado'), ('C', 'Cancelado'), ('R', 'Rechazado'),)
    WAY_PAY_CHOICES = (('E', 'Efectivo'), ('T', 'Tarjeta de credito'),)
    customer = models.ForeignKey(Customer, verbose_name='Cliente', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name='Empleado', on_delete=models.CASCADE)
    charged = models.DecimalField(
        max_digits=10, verbose_name='Importe cobrado', decimal_places=2, default=0)
    received = models.DecimalField(
        max_digits=10, verbose_name='Importe recibido', decimal_places=2, default=0)
    turned = models.DecimalField(
        max_digits=10, verbose_name='Importe devuelto', decimal_places=2, default=0)
    status = models.CharField(max_length=1, verbose_name='Estado',
                              choices=STATUS_CHOICES, default='A', )
    way_pay = models.CharField(max_length=1, verbose_name='Forma de pago',
                               choices=WAY_PAY_CHOICES, default='E', )
    sale_date = models.DateField(verbose_name='Fecha de venta', null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación', null=True, blank=True)
    branch_office = models.ForeignKey(
        BranchOffice, verbose_name='Sucursal', blank=True, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.customer.user.first_name

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    @property
    def total_gain_obtained(self):
        total = 0
        for detail in self.detail_sales.all():
            total += detail.profit_per_product_in_sales_obtained
        return total

    @property
    def total_gain_estimated(self):
        total = 0
        for detail in self.detail_sales.all():
            total += detail.profit_per_product_in_sales_estimated
        return total

    @property
    def total_discount(self):
        total = 0
        for detail in self.detail_sales.all():
            total += detail.discount_per_product_in_sales
        return total


class ProductReturn(models.Model):
    TYPE_CHOICES = (('V', 'Devolución de venta'), ('C', 'Devolución de compra'),)
    STATUS_CHOICES = (('A', 'Activo'), ('I', 'Inactivo'),)
    purchase = models.ForeignKey(Purchase, verbose_name='Compra',
                                 null=True, blank=True, on_delete=models.CASCADE)
    sales = models.ForeignKey(Sales, verbose_name='Venta', null=True,
                              blank=True, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name='Empleado', on_delete=models.CASCADE)
    type = models.CharField(max_length=1, verbose_name='Tipo', choices=TYPE_CHOICES)
    status = models.CharField(max_length=1, verbose_name='Estado',
                              choices=STATUS_CHOICES, default='A', )
    motive = models.CharField(max_length=150, verbose_name='Motivo', null=True, blank=True)
    comment = models.TextField(max_length=2000, verbose_name='Descripción', blank=True, null=True)
    return_date = models.DateField(verbose_name='Fecha de devolución', null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación', null=True, blank=True)

    def __unicode__(self):
        return self.quantity_shipped

    class Meta:
        verbose_name = 'Devolución del producto'
        verbose_name_plural = 'Devolución de productos'


class AcquisitionDetail(models.Model):
    rate_estimated = models.DecimalField(
        max_digits=10, verbose_name='Tarifa estimada', decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=10, verbose_name='Tarifa', decimal_places=2, default=0)
    quantity_ordered = models.IntegerField(
        default=0, verbose_name='Cantidad ordenada', null=True, blank=True)
    quantity_received = models.IntegerField(
        default=0, verbose_name='Cantidad recibido', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, verbose_name='Importe', decimal_places=2, default=0)
    product = models.ForeignKey(Product, verbose_name='Producto', on_delete=models.CASCADE)
    purchase = models.ForeignKey(Purchase, related_name='detail_purchases',
                                 verbose_name='Compra', null=True, blank=True, on_delete=models.CASCADE)
    sales = models.ForeignKey(Sales, related_name='detail_sales',
                              verbose_name='Venta', null=True, blank=True, on_delete=models.CASCADE)
    product_return = models.ForeignKey(
        ProductReturn, related_name='detail_returns', verbose_name='Devolución', null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.product.name

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = 'Detalle de adquisición'
        verbose_name_plural = 'Detalles de adquisición'

    @property
    def gain(self):
        return (self.product.sale_price - self.rate) * self.quantity_ordered

    @property
    def amount_estimated(self):
        return self.product.sale_price * self.quantity_ordered

    @property
    def profit_per_product(self):
        return self.product.sale_price - self.rate

    @property
    def profit_per_product_in_sales_obtained(self):
        total = 0
        for detail in self.acquisitions.all():
            total += detail.profit_obtained
        return total

    @property
    def profit_per_product_in_sales_estimated(self):
        total = 0
        for detail in self.acquisitions.all():
            total += detail.profit_estimated
        return total

    @property
    def discount_per_product_in_sales(self):
        total = 0
        for detail in self.acquisitions.all():
            total += detail.discount
        return total

    @property
    def total_sale_price(self):
        return self.product.sale_price * self.quantity_ordered


class Batch(models.Model):
    product = models.ForeignKey(Product, verbose_name='Producto',
                                related_name='batches', on_delete=models.CASCADE)
    barcode = models.TextField(max_length=100, verbose_name='BarCode', unique=True)
    due_date = models.DateField(verbose_name='Fecha de vencimiento', null=True, blank=True)
    entry_date = models.DateField(verbose_name='Fecha de entrada', null=True, blank=True)
    edition = models.IntegerField(default=0, verbose_name='Edición', null=True, blank=True)
    total_quantity = models.IntegerField(default=0, verbose_name='Cantidad', null=True, blank=True)

    def __unicode__(self):
        return self.product.name

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'


class BatchDetail(models.Model):
    TYPE_CHOICES = (('V', 'Venta'), ('C', 'Compra'),
                    ('D', 'Devolucion de compra'), ('R', 'Devolucion de  venta'),)
    batch = models.ForeignKey(Batch, verbose_name='Lote',
                              related_name='detail_batches', on_delete=models.CASCADE)
    type = models.CharField(max_length=1, verbose_name='Tipo', choices=TYPE_CHOICES)
    entry_date = models.DateField(verbose_name='Fecha de entrada', null=True, blank=True)
    quantity = models.IntegerField(default=0, verbose_name='Cantidad', null=True, blank=True)
    acquisition_detail = models.ForeignKey(
        AcquisitionDetail, related_name='acquisitions', verbose_name='Detalle de adquisición', null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.batch.product.name

    def __str__(self):
        return self.batch.product.name

    class Meta:
        verbose_name = 'Detalle de lote'
        verbose_name_plural = 'Detalle de lotes'

    @property
    def subtotal(self):
        return self.acquisition_detail.rate * self.quantity

    @property
    def profit_obtained(self):
        detail = BatchDetail.objects.filter(batch_id__exact=self.batch.id, type='C').first()
        purchase_price = detail.acquisition_detail.rate
        return (self.acquisition_detail.rate - purchase_price) * self.quantity

    @property
    def profit_estimated(self):
        detail = BatchDetail.objects.filter(batch_id__exact=self.batch.id, type='C').first()
        purchase_price = detail.acquisition_detail.rate
        return (self.acquisition_detail.rate_estimated - purchase_price) * self.quantity

    @property
    def discount(self):
        return (self.acquisition_detail.rate_estimated - self.acquisition_detail.rate) * self.quantity

    @property
    def excess_stock_price(self):
        return self.batch.product.sale_price * self.batch.total_quantity
        # return self.acquisition_detail.rate * self.batch.total_quantity

    @property
    def remaining_stock_gain(self):
        return (self.batch.product.sale_price - self.acquisition_detail.rate) * self.batch.total_quantity


class Kardex(models.Model):
    product = models.ForeignKey(Product, verbose_name='Producto', on_delete=models.CASCADE)
    purchase = models.ForeignKey(Purchase, verbose_name='Compra',
                                 null=True, blank=True, on_delete=models.CASCADE)
    sales = models.ForeignKey(Sales, verbose_name='Venta', null=True,
                              blank=True, on_delete=models.CASCADE)
    product_return = models.ForeignKey(
        ProductReturn, verbose_name='Devolución', null=True, blank=True, on_delete=models.CASCADE)
    acquisition_detail = models.ForeignKey(
        AcquisitionDetail, verbose_name='Detalle de adquisición', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')

    def __unicode__(self):
        return self.product.name

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = 'Kardex'
        verbose_name_plural = 'Kardex'


class Expense(models.Model):
    description = models.CharField(max_length=200, verbose_name='Descripción')
    rode = models.DecimalField(max_digits=10, verbose_name='Importe', decimal_places=2, default=0)
    employee = models.ForeignKey(Employee, verbose_name='Empleado',
                                 null=True, blank=True, on_delete=models.CASCADE)
    expense_date = models.DateField(verbose_name='Fecha de gasto', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    branch_office = models.ForeignKey(
        BranchOffice, verbose_name='Sucursal', blank=True, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.description

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'


class WayPay(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre', unique=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Forma de pago'
        verbose_name_plural = 'Formas de pago'


class RegistrationPaymentMethod(models.Model):
    rode = models.DecimalField(max_digits=10, verbose_name='Monto', decimal_places=2, default=0)
    way_pay = models.ForeignKey(WayPay, verbose_name='Forma de pago', on_delete=models.CASCADE)
    sales = models.ForeignKey(Sales, related_name='registration_payment_methods',
                              verbose_name='Venta', on_delete=models.CASCADE, null=True, blank=True)
    product_return = models.ForeignKey(
        ProductReturn, verbose_name='Devolución', null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.rode

    class Meta:
        verbose_name = 'Registro del método de pago'
        verbose_name_plural = 'Registro del métodos de pago'
