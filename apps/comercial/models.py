from django.db import models
from django.contrib.auth.models import User
from apps.hrm.models import Subsidiary, Employee
from apps.sales.models import Client, Product, Unit, SubsidiaryStore, Order, OrderDetail, ProductDetail
from django.db.models import Sum
from django.db.models import Q


# Create your models here.


class Owner(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=500, unique=True)
    ruc = models.CharField(max_length=11)
    address = models.CharField('Dirección', max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Propietario'
        verbose_name_plural = 'Propietarios'


class TruckBrand(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Marca de tracto'
        verbose_name_plural = 'Marcas de tractos'


class TruckModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    truck_brand = models.ForeignKey('TruckBrand', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Modelo de tracto'
        verbose_name_plural = 'Modelos de tractos'


class Truck(models.Model):
    DRIVE_TYPE_CHOICES = (('S', 'SEMITRAILER'), ('C', 'CAMION'), ('R', 'UNIDAD DE REPARTO'),)
    FUEL_TYPE_CHOICES = (('1', 'DIESEL'), ('2', 'GASOLINA'), ('3', 'GAS'),)
    CONDITION_OWNER_CHOICES = (('P', 'PROPIO'), ('A', 'ALQUILADO'),)
    id = models.AutoField(primary_key=True)
    license_plate = models.CharField('Placa', max_length=10, unique=True)
    num_axle = models.IntegerField('Numero de Ejes', null=True, default=0)
    year = models.CharField('Fabricación', max_length=4, null=True, blank=True)
    truck_model = models.ForeignKey('TruckModel', on_delete=models.SET_NULL, null=True, blank=True)
    drive_type = models.CharField('Tipo de Unidad', max_length=2,
                                  choices=DRIVE_TYPE_CHOICES, default='S')
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    contact_phone = models.CharField(max_length=45, null=True, blank=True)
    certificate = models.CharField(max_length=10, null=True, blank=True)
    serial = models.CharField(max_length=5, null=True, blank=True)
    engine = models.CharField('Motor', max_length=100, null=True, blank=True)
    chassis = models.CharField('Chasis', max_length=100, null=True, blank=True)
    color = models.CharField(max_length=45, null=True, blank=True)
    fuel_type = models.CharField('Tipo de Combustible', max_length=1,
                                 choices=FUEL_TYPE_CHOICES, default='1')
    owner = models.ForeignKey('Owner', on_delete=models.SET_NULL, null=True, blank=True)
    condition_owner = models.CharField('Condicion', max_length=1,
                                       choices=CONDITION_OWNER_CHOICES, default='P')
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.license_plate

    class Meta:
        verbose_name = 'Tracto'
        verbose_name_plural = 'Tractos'


class Driver(models.Model):
    LICENSE_TYPE_CHOICES = (
        ('1', 'A-I'), ('2', 'A-IIB'), ('3', 'A-IIIC'), ('4', 'A-IIIB'), ('5', 'A-IVA'), ('6', 'A-IIA'),
        ('7', 'A-IIIA'), ('8', 'B-I'), ('9', 'B-IIA'), ('10', 'B-IIB'), ('11', 'B-IIC'), ('12', 'SIN LICENCIA'),)
    id = models.AutoField(primary_key=True)
    names = models.CharField(max_length=40, null=True, blank=True)
    birthdate = models.DateField('Fecha de nacimiento', null=True, blank=True)
    document_driver = models.CharField(max_length=12, null=True, blank=True)
    n_license = models.CharField(max_length=12, null=True, blank=True)
    license_type = models.CharField('Tipo de licencia', max_length=2,
                                    choices=LICENSE_TYPE_CHOICES, default='12', )
    license_expiration_date = models.DateField(
        'Fecha de expiracion de licencia', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.names


class TruckAssociate(models.Model):
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey('Truck', on_delete=models.CASCADE)
    driver = models.ForeignKey('Driver', verbose_name='Piloto Asociado', on_delete=models.SET_NULL, null=True,
                               blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Pilotos Asociado'
        verbose_name_plural = 'Pilotos Asociados'


class TowingBrand(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Marca de furgon'
        verbose_name_plural = 'Marcas de furgones'


class TowingModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    towing_brand = models.ForeignKey(
        'TowingBrand', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Modelo de furgon'
        verbose_name_plural = 'Modelos de furgones'


class Towing(models.Model):
    TOWING_TYPE_CHOICES = (('F', 'FURGON'), ('C', 'CISTERNA'), ('P', 'PLATAFORMA'),)
    CONDITION_OWNER_CHOICES = (('P', 'PROPIO'), ('A', 'ALQUILADO'),)
    id = models.AutoField(primary_key=True)
    license_plate = models.CharField('Placa', max_length=10, unique=True)
    num_axle = models.IntegerField('Numero de Ejes', null=True, default=0)
    weight_towing = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    year = models.CharField('Fabricación', max_length=4, null=True, blank=True)
    color = models.CharField(max_length=45, null=True, blank=True)
    denomination = models.CharField(max_length=15, null=True, blank=True)
    towing_model = models.ForeignKey(
        'TowingModel', on_delete=models.SET_NULL, null=True, blank=True)
    towing_type = models.CharField('Condicion', max_length=1,
                                   choices=TOWING_TYPE_CHOICES, default='F')
    is_available = models.BooleanField('Condicion', default=True)
    owner = models.ForeignKey('Owner', on_delete=models.SET_NULL, null=True, blank=True)
    condition_owner = models.CharField('Condicion', max_length=1,
                                       choices=CONDITION_OWNER_CHOICES, default='P')

    def __str__(self):
        return self.license_plate

    class Meta:
        verbose_name = 'Furgon'
        verbose_name_plural = 'Furgones'


class Programming(models.Model):
    STATUS_CHOICES = (('P', 'Programado'), ('R', 'En Ruta'),
                      ('F', 'Finalizado'), ('C', 'Cancelado'))
    TYPE_CHOICES = (('G', 'Flota Grande'), ('P', 'Flota Pequeña'), ('R', 'Reparto'))
    id = models.AutoField(primary_key=True)
    departure_date = models.DateField('Fecha Salida', null=True, blank=True)
    arrival_date = models.DateField('Fecha Llegada', null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, null=True, )
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    truck = models.ForeignKey('Truck', verbose_name='Tracto',
                              on_delete=models.SET_NULL, null=True, blank=True)
    towing = models.ForeignKey('Towing', verbose_name='Furgon',
                               on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, verbose_name='Sede',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    observation = models.CharField(max_length=200, null=True, blank=True)
    order = models.IntegerField('Turno', default=0)
    km_initial = models.CharField('km inicial', max_length=6, null=True, blank=True)
    km_ending = models.CharField('km inicial', max_length=6, null=True, blank=True)

    def __str__(self):
        # return str(self.subsidiary.name) + "/" + str(self.departure_date)
        return str(self.id)

    def get_pilot(self):
        set_employee_set = SetEmployee.objects.filter(programming=self.id, function='P')
        pilot = None
        if set_employee_set.count() > 0:
            pilot = set_employee_set.first().employee
        return pilot

    def get_route(self):
        origin_set = Route.objects.filter(programming=self.id, type='O')
        origin = None
        if origin_set.count() > 0:
            origin = origin_set.first().subsidiary.name
        destiny_set = Route.objects.filter(programming=self.id, type='D')
        destiny = None
        if destiny_set.count() > 0:
            destiny = destiny_set.first().subsidiary.name
        route_ = origin + " - " + destiny
        return route_

    def get_origin(self):
        origin = None
        origin_set = Route.objects.filter(programming=self.id, type='O')
        if origin_set.count() > 0:
            origin = origin_set.first().subsidiary
        return origin

    def get_destiny(self):
        destiny = None
        destiny_set = Route.objects.filter(programming=self.id, type='D')
        if destiny_set.count() > 0:
            destiny = destiny_set.first().subsidiary
        return destiny

    class Meta:
        verbose_name = 'Programación'
        verbose_name_plural = 'Programaciones'


class SetEmployee(models.Model):
    FUNCTION_CHOICES = (('R', 'Responsable'), ('P', 'Piloto'),
                        ('C', 'COPILOTO'), ('E', 'Estibador'),)
    id = models.AutoField(primary_key=True)
    programming = models.ForeignKey('Programming', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    function = models.CharField('Función', max_length=1, choices=FUNCTION_CHOICES, default='P', )

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Cuadrilla'
        verbose_name_plural = 'Cuadrillas'


class GuideMotive(models.Model):
    TYPE_CHOICES = (('E', 'ENTRADA'), ('S', 'SALIDA'))
    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='E', )
    code = models.CharField(max_length=5, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Motivo'
        verbose_name_plural = 'Motivos'


class Guide(models.Model):
    STATUS_CHOICES = (('1', 'En transito'), ('2', 'Aprobada'), ('3', 'Entregada'), ('4', 'Anulada'), ('5', 'Extraido'),)
    DOCUMENT_TYPE_ATTACHED_CHOICES = (
        ('G', 'Guia de remision'), ('F', 'Factura'), ('P', 'Orden de produccion'), ('T', 'Transferencia de almacen'),
        ('O', 'Otro'))
    MODALITY_TRANSPORT_CHOICES = (('1', 'PUBLICO'), ('2', 'PRIVADO'))
    id = models.AutoField(primary_key=True)
    serial = models.CharField('Serie', max_length=10, null=True, blank=True)
    correlative = models.CharField('Correlativo', max_length=20, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='1', )
    document_type_attached = models.CharField('Tipo documento', max_length=1, choices=DOCUMENT_TYPE_ATTACHED_CHOICES,
                                              default='G', )
    observation = models.CharField(max_length=500, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    guide_motive = models.ForeignKey('GuideMotive', on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, verbose_name='Sede', on_delete=models.SET_NULL, null=True, blank=True)
    origin = models.CharField('Ubigeo Origen', max_length=10, null=True, blank=True)
    origin_address = models.CharField('Direccion Origen', max_length=200, null=True, blank=True)
    destiny = models.CharField('Ubigeo Destino', max_length=10, null=True, blank=True)
    destiny_address = models.CharField('Direccion Destino', max_length=200, null=True, blank=True)
    modality_transport = models.CharField('Modalidad de transporte guia', max_length=1,
                                          choices=MODALITY_TRANSPORT_CHOICES, default='1')
    carrier = models.ForeignKey(Owner, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(Truck, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    weight = models.DecimalField('Peso', max_digits=30, decimal_places=4, default=0)
    package = models.DecimalField('Bulto', max_digits=30, decimal_places=4, default=0)
    date_issue = models.DateTimeField(null=True, blank=True)
    transfer_date = models.DateTimeField(null=True, blank=True)
    contract_detail = models.ForeignKey('buys.ContractDetail', on_delete=models.CASCADE, null=True, blank=True)
    register_mtc = models.CharField('MTC', max_length=50, null=True, blank=True)
    order_buy = models.CharField('Orden de Compra', max_length=50, null=True, blank=True)

    def __str__(self):
        return str(self.serial) + "-" + str(self.correlative)

    def get_origin(self):
        origin_set = Route.objects.filter(guide__id=self.id, type='O')
        origin = None
        if origin_set.count() > 0:
            origin = origin_set.last().subsidiary_store
        return origin

    def get_destiny(self):
        destiny_set = Route.objects.filter(guide__id=self.id, type='D')
        destiny = None
        if destiny_set.count() > 0:
            destiny = destiny_set.last().subsidiary_store
        return destiny

    def the_one_that_approves(self):
        guide_employee_set = GuideEmployee.objects.filter(guide__id=self.id, function='A')
        guide_employee = None
        if guide_employee_set.count() > 0:
            guide_employee = guide_employee_set.last()
        return guide_employee

    def the_one_that_requests(self):
        guide_employee_set = GuideEmployee.objects.filter(guide__id=self.id, function='S')
        guide_employee = None
        if guide_employee_set.count() > 0:
            guide_employee = guide_employee_set.last()
        return guide_employee

    def the_one_that_receives(self):
        guide_employee_set = GuideEmployee.objects.filter(guide__id=self.id, function='R')
        guide_employee = None
        if guide_employee_set.count() > 0:
            guide_employee = guide_employee_set.last()
        return guide_employee

    def the_one_that_cancel(self):
        guide_employee_set = GuideEmployee.objects.filter(guide__id=self.id, function='C')
        guide_employee = None
        if guide_employee_set.count() > 0:
            guide_employee = guide_employee_set.last()
        return guide_employee

    def get_serial(self):
        serial = ''
        if self.guide_motive:
            serial = '{}{}'.format(self.guide_motive.type, self.guide_motive.id)
        return serial

    class Meta:
        verbose_name = 'Guia'
        verbose_name_plural = 'Guias'


class GuideDetail(models.Model):
    id = models.AutoField(primary_key=True)
    guide = models.ForeignKey('Guide', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # quantity_request = models.DecimalField('Cantidad pedida', max_digits=10, decimal_places=2, default=0)
    # quantity_sent = models.DecimalField('Cantidad enviada', max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Detalle guia'
        verbose_name_plural = 'Detalles de guias'


class Route(models.Model):
    TYPE_CHOICES = (('O', 'Origen'), ('D', 'Destino'),)
    id = models.AutoField(primary_key=True)
    programming = models.ForeignKey('Programming', on_delete=models.CASCADE, null=True, blank=True)
    guide = models.ForeignKey('Guide', on_delete=models.CASCADE, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, verbose_name='Sede', on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary_store = models.ForeignKey(SubsidiaryStore, verbose_name='Almacen', on_delete=models.SET_NULL, null=True,
                                         blank=True)
    type = models.CharField('Tipo de Ruta', max_length=1, choices=TYPE_CHOICES, default='O', )

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Ruta'
        verbose_name_plural = 'Rutas'


class GuideEmployee(models.Model):
    FUNCTION_CHOICES = (('S', 'Solicita'), ('A', 'Aprueba'),
                        ('R', 'Recibe'), ('C', 'Cancela'), ('E', 'Ejecuta'),)
    id = models.AutoField(primary_key=True)
    guide = models.ForeignKey('Guide', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    function = models.CharField('Función', max_length=1, choices=FUNCTION_CHOICES, default='S', )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Actor'
        verbose_name_plural = 'Actores'


class DistributionMobil(models.Model):
    STATUS_CHOICES = (('P', 'PROGRAMADO'), ('F', 'FINALIZADO'), ('A', 'ANULADO'),)
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey('Truck', verbose_name='Tracto',
                              on_delete=models.SET_NULL, null=True, blank=True)
    date_distribution = models.DateField('Fecha de Distribucion', null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    pilot = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guide_number = models.CharField('Numero guia', max_length=20, null=True, blank=True)

    def new_detail_distribution(self):
        response = DistributionDetail.objects.filter(
            distribution_mobil_id=self.id).exclude(status='D')

        product_dict = {}
        for d in response:
            _search_value = d.product.id
            if _search_value in product_dict.keys():
                _product = product_dict[d.product.id]
                _expenses = _product.get('i_expenses')
                _returned = _product.get('i_returned')
                _advanced = _product.get('i_advanced')
                _recovered = _product.get('i_recovered')
                _sold = _product.get('i_sold')
                _ball = _product.get('i_ball')
                _sold_bg = _product.get('i_sold_bg')

                if d.status == 'E':
                    if d.type == 'L':
                        product_dict[d.product.id]['i_expenses'] = d.quantity
                        _sold = d.calculate_total_quantity_sold_by_product_glp()
                        _returned = d.quantity - _sold
                        _ball = _ball + d.calculate_total_quantity_sold_by_product() - d.calculate_total_quantity_container_sold_by_product()
                        _sold_bg = d.calculate_total_quantity_container_sold_by_product()
                        product_dict[d.product.id]['i_sold'] = _sold
                        product_dict[d.product.id]['i_returned'] = _returned
                        product_dict[d.product.id]['i_ball'] = _ball
                        product_dict[d.product.id]['i_sold_bg'] = _sold_bg

                    elif d.type == 'V':
                        product_dict[d.product.id]['i_ball'] = _ball + d.quantity

                if d.status == 'R':
                    product_dict[d.product.id]['i_recovered'] = d.quantity
                    _ball = _ball + d.quantity
                    product_dict[d.product.id]['i_ball'] = _ball

                if d.status == 'A':
                    product_dict[d.product.id]['i_advanced'] = d.quantity
                    _ball = _ball + d.quantity
                    product_dict[d.product.id]['i_ball'] = _ball

            else:
                if d.status == 'E':
                    if d.type == 'L':
                        _sold = d.calculate_total_quantity_sold_by_product_glp()
                        _returned = d.quantity - _sold
                        product_dict[d.product.id] = {
                            'i_expenses': d.quantity,
                            'i_returned': _returned,
                            'i_advanced': 0,
                            'i_sold': _sold,
                            'i_recovered': 0,
                            'i_ball': d.calculate_total_quantity_sold_by_product() - d.calculate_total_quantity_container_sold_by_product(),
                            'i_sold_bg': d.calculate_total_quantity_container_sold_by_product(),
                            'pk': d.product.id,
                            'name': d.product.name
                        }
                    elif d.type == 'V':
                        product_dict[d.product.id] = {
                            'i_expenses': 0,
                            'i_returned': 0,
                            'i_advanced': 0,
                            'i_sold': 0,
                            'i_recovered': 0,
                            'i_ball': d.quantity,
                            'i_sold_bg': 0,
                            'pk': d.product.id,
                            'name': d.product.name
                        }
                if d.status == 'R':
                    _sold = d.calculate_total_quantity_sold_by_product_glp()
                    product_dict[d.product.id] = {
                        'i_expenses': 0,
                        'i_returned': 0,
                        'i_advanced': 0,
                        'i_sold': _sold,
                        'i_recovered': d.quantity,
                        'i_ball': d.quantity,
                        'i_sold_bg': 0,
                        'pk': d.product.id,
                        'name': d.product.name}
                if d.status == 'A':
                    _sold = d.calculate_total_quantity_sold_by_product_glp()
                    product_dict[d.product.id] = {
                        'i_expenses': 0,
                        'i_returned': 0,
                        'i_sold': _sold,
                        'i_advanced': d.quantity,
                        'i_recovered': 0,
                        'i_ball': d.quantity,
                        'i_sold_bg': 0,
                        'pk': d.product.id,
                        'name': d.product.name}

        return product_dict

    def __str__(self):
        return str(self.id)


class DistributionDetail(models.Model):
    STATUS_CHOICES = (('E', 'EGRESO'), ('D', 'DEVOLUCION'), ('C', 'EN CARRO'), ('R', 'RECUPERADO'), ('A', 'ADELANTO'))
    TYPE_CHOICES = (('V', 'VACIOS'), ('L', 'LLENOS'), ('M', 'MALOGRADOS'), ('VM', 'VACIO(S) MALOGRADO(S)'),)
    distribution_mobil = models.ForeignKey(DistributionMobil, on_delete=models.SET_NULL, null=True,
                                           blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='E', )
    type = models.CharField('Tipo', max_length=2, choices=TYPE_CHOICES, default='L', )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    def calculate_total_b_quantity(self):
        response = DistributionDetail.objects.filter(
            distribution_mobil_id=self.distribution_mobil.id, status='E').values(
            'distribution_mobil').annotate(totals=Sum('quantity'))
        # return response.count
        return response[0].get('totals')

    def calculate_total_quantity_sold_by_product(self):
        sales_set = Order.objects.filter(distribution_mobil=self.distribution_mobil)
        quantity_total = 0
        for s in sales_set.all():
            for d in s.orderdetail_set.all():
                if d.unit.name == 'G' and d.product == self.product:
                    quantity_total = quantity_total + d.quantity_sold
        return quantity_total

    def calculate_total_quantity_sold_by_product_glp(self):
        sales_set = Order.objects.filter(distribution_mobil=self.distribution_mobil)
        quantity_total = 0
        for s in sales_set.all():
            for d in s.orderdetail_set.all():
                if (d.unit.name == 'G' or d.unit.name == 'GBC') and d.product == self.product:
                    quantity_total = quantity_total + d.quantity_sold
        return quantity_total

    def calculate_total_quantity_container_sold_by_product(self):
        sales_container_set = Order.objects.filter(distribution_mobil=self.distribution_mobil)
        quantity_container = 0
        for s in sales_container_set.all():
            for d in s.orderdetail_set.all():
                if d.unit.name == 'B' and d.product == self.product:
                    quantity_container = quantity_container + d.quantity_sold
        return quantity_container

    def return_quantity_r(self):
        response = 0
        distribution_detail = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                product=self.product,
                                                                status='R')
        if distribution_detail.count() > 0:
            response = distribution_detail.first().quantity
        return response

    def return_quantity_a(self):
        response = 0
        distribution_detail = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                product=self.product,
                                                                status='A')
        if distribution_detail.count() > 0:
            response = distribution_detail.first().quantity
        return response

    def has_detail_e_by_r(self):
        response = False
        if self.status == 'R':
            distribution_detail_e = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                      product=self.product, status='E')
            if distribution_detail_e.count() > 0:
                response = True
        return response

    def has_detail_a_by_r(self):
        response = False
        if self.status == 'R':
            distribution_detail_e = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                      product=self.product, status='A')
            if distribution_detail_e.count() > 0:
                response = True
        return response

    def has_detail_r_by_a(self):
        response = False
        if self.status == 'A':
            distribution_detail_r = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                      product=self.product, status='R')
            if distribution_detail_r.count() > 0:
                response = True
        return response

    def has_detail_e_by_a(self):
        response = False
        if self.status == 'A':
            distribution_detail_e = DistributionDetail.objects.filter(distribution_mobil=self.distribution_mobil,
                                                                      product=self.product, status='E')
            if distribution_detail_e.count() > 0:
                response = True
        return response