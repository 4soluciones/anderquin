from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class DocumentType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Tipo de documento de identidad'
        verbose_name_plural = 'Tipos de documento de identidad'


class DocumentIssuingCountry(models.Model):
    id = models.CharField(primary_key=True, max_length=3)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'País emisor del documento'
        verbose_name_plural = 'Países emisores del documento'


class Nationality(models.Model):
    id = models.CharField(primary_key=True, max_length=4)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Nacionalidad'
        verbose_name_plural = 'Nacionalidades'


class RoadType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Vía'
        verbose_name_plural = 'Vías'


class ZoneType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Zona'
        verbose_name_plural = 'Zonas'


class Department(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'


class Province(models.Model):
    id = models.CharField(primary_key=True, max_length=4)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Provincia'
        verbose_name_plural = 'Provincias'


class District(models.Model):
    id = models.CharField(primary_key=True, max_length=6)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Distrito'
        verbose_name_plural = 'Distritos'


class TelephoneNationalLongDistanceCode(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Código de larga distancia nacional'
        verbose_name_plural = 'Códigos de larga distancia nacional'


class Employee(models.Model):
    GENDER_CHOICES = (('1', 'masculino'), ('2', 'femenino'),)
    CENTER_INDICATOR_CHOICES = (('1', 'direccion 1'), ('2', 'direccion 2'),)
    LICENSE_TYPE_CHOICES = (('1', 'A-I'), ('2', 'A-IIB'), ('3', 'A-IIIC'), ('4', 'A-IIIB'), ('5', 'A-IVA'), ('6', 'A-IIA'),
                            ('7', 'A-IIIA'), ('8', 'B-I'), ('9', 'B-IIA'), ('10', 'B-IIB'), ('11', 'B-IIC'), ('12', 'SIN LICENCIA'),)
    ESSALUD_ASSISTANCE_CHOICES = (('1', 'dirección 1'), ('2', ' dirección 2'),)

    document_type = models.ForeignKey('DocumentType', on_delete=models.CASCADE)
    document_number = models.CharField(max_length=15, null=True, blank=True)
    document_issuing_country = models.ForeignKey('DocumentIssuingCountry', on_delete=models.CASCADE)
    birthdate = models.DateField('Fecha de nacimiento', null=True, blank=True)
    paternal_last_name = models.CharField(max_length=40, null=True, blank=True)
    maternal_last_name = models.CharField(max_length=40, null=True, blank=True)
    names = models.CharField(max_length=40, null=True, blank=True)
    gender = models.CharField('Sexo', max_length=1, choices=GENDER_CHOICES, default='1', )
    nationality = models.ForeignKey('Nationality', on_delete=models.CASCADE)
    telephone_national_long_distance_code = models.ForeignKey(
        'TelephoneNationalLongDistanceCode', related_name='cldn', on_delete=models.SET_NULL, null=True, blank=True)
    telephone_number = models.CharField(max_length=9, null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)

    address_1_road_type = models.ForeignKey(
        'RoadType', related_name='road_type_add_1', on_delete=models.SET_NULL, null=True, blank=True)
    address_1_road_name = models.CharField(max_length=20, null=True, blank=True)
    address_1_road_number = models.CharField(max_length=4, null=True, blank=True)
    address_1_department = models.CharField(max_length=4, null=True, blank=True)
    address_1_interior = models.CharField(max_length=4, null=True, blank=True)
    address_1_apple = models.CharField(max_length=4, null=True, blank=True)
    address_1_lot = models.CharField(max_length=4, null=True, blank=True)
    address_1_kilometer = models.CharField(max_length=4, null=True, blank=True)
    address_1_block = models.CharField(max_length=4, null=True, blank=True)
    address_1_stage = models.CharField(max_length=4, null=True, blank=True)
    address_1_zone_type = models.ForeignKey(
        'ZoneType', related_name='zone_type_add_1', on_delete=models.SET_NULL, null=True, blank=True)
    address_1_zone_name = models.CharField(max_length=20, null=True, blank=True)
    address_1_reference = models.CharField(max_length=40, null=True, blank=True)
    address_1_district = models.ForeignKey(
        'District', related_name='district_add_1', on_delete=models.SET_NULL, null=True, blank=True)

    address_2_road_type = models.ForeignKey(
        'RoadType', related_name='road_type_add_2', on_delete=models.SET_NULL, null=True, blank=True)
    address_2_road_name = models.CharField(max_length=20, null=True, blank=True)
    address_2_road_number = models.CharField(max_length=4, null=True, blank=True)
    address_2_department = models.CharField(max_length=4, null=True, blank=True)
    address_2_interior = models.CharField(max_length=4, null=True, blank=True)
    address_2_apple = models.CharField(max_length=4, null=True, blank=True)
    address_2_lot = models.CharField(max_length=4, null=True, blank=True)
    address_2_kilometer = models.CharField(max_length=4, null=True, blank=True)
    address_2_block = models.CharField(max_length=4, null=True, blank=True)
    address_2_stage = models.CharField(max_length=4, null=True, blank=True)
    address_2_zone_type = models.ForeignKey(
        'ZoneType', related_name='zone_type_add_2', on_delete=models.SET_NULL, null=True, blank=True)
    address_2_zone_name = models.CharField(max_length=20, null=True, blank=True)
    address_2_reference = models.CharField(max_length=40, null=True, blank=True)
    address_2_district = models.ForeignKey(
        'District', related_name='district_add_2', on_delete=models.SET_NULL, null=True, blank=True)
    essalud_assistance = models.CharField(
        'Centro asistencial', max_length=1, choices=ESSALUD_ASSISTANCE_CHOICES, default='1', )
    n_license = models.CharField(max_length=12, null=True, blank=True)
    license_type = models.CharField('Tipo de licencia', max_length=2,
                                    choices=LICENSE_TYPE_CHOICES, default='12', )
    license_expiration_date = models.DateField(
        'Fecha de expiracion de licencia', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.pk)

    def full_name(self):
        # return str(self.names) + ' ' + str(self.paternal_last_name) + ' ' + str(self.maternal_last_name)
        return '{} {} {}'.format(self.names, self.paternal_last_name, self.maternal_last_name)

    class Meta:
        verbose_name = 'Datos personales del trabajador'
        verbose_name_plural = 'Datos personales de los trabajadores'


class LaborRegime(models.Model):
    PRIVATE_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    PUBLIC_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    OTHER_ENTITIES_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)
    private_sector = models.CharField('Sector Privado', max_length=3,
                                      choices=PRIVATE_SECTOR_CHOICES, default='A', )
    public_sector = models.CharField('Sector Publico', max_length=3,
                                     choices=PUBLIC_SECTOR_CHOICES, default='A', )
    other_entities = models.CharField(
        'Otras entidades', max_length=3, choices=OTHER_ENTITIES_CHOICES, default='A', )

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Régimen laboral'
        verbose_name_plural = 'Régimenes laborales'


class EducationalSituation(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Situación educativa'
        verbose_name_plural = 'Situaciones educativas'


class OccupationPrivateSector(models.Model):
    id = models.CharField(primary_key=True, max_length=6)
    name = models.CharField(max_length=200)
    executive = models.BooleanField(default=False)
    employee = models.BooleanField(default=False)
    worker = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Ocupación aplicable a los empleadores del sector privado'
        verbose_name_plural = 'Ocupaciones aplicable a los empleadores del sector privado'


class OccupationPublicSector(models.Model):
    id = models.CharField(primary_key=True, max_length=6)
    name = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Ocupación de trabaj (del sector público y otras entidades) y personal en formación modalidad formativa laboraL'
        verbose_name_plural = 'Ocupaciones de trabaj (del sector público y otras entidades) y personal en formación modalidad formativa laboraL'


class OccupationalCategory(models.Model):
    PRIVATE_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    PUBLIC_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    OTHER_ENTITIES_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)
    private_sector = models.CharField('Sector Privado', max_length=3,
                                      choices=PRIVATE_SECTOR_CHOICES, default='A', )
    public_sector = models.CharField('Sector Publico', max_length=3,
                                     choices=PUBLIC_SECTOR_CHOICES, default='A', )
    other_entities = models.CharField(
        'Otras entidades', max_length=3, choices=OTHER_ENTITIES_CHOICES, default='A', )

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Categoría ocupacional del trabajador'
        verbose_name_plural = 'Categorías ocupacionales del trabajador'


class ContractType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    name = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Tipo de contrato de trabajo/condición laboral'
        verbose_name_plural = 'Tipos de contratos de trabajo/condición laboral'


class Situation(models.Model):
    id = models.CharField(primary_key=True, max_length=1)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Situación del trabajador o pensionista'
        verbose_name_plural = 'Situaciones del trabajador o pensionista'


class SpecialSituation(models.Model):
    id = models.CharField(primary_key=True, max_length=1)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Situación especial'
        verbose_name_plural = 'Situaciones especiales'


class Worker(models.Model):
    SCTR_PENSION_CHOICES = (('0', 'Ninguno'), ('1', 'ONP'), ('2', 'Cía privada'),)
    PERIODICITY_CHOICES = (('1', 'MENSUAL'), ('2', 'QUINCENAL'),
                           ('3', 'SEMANAL'), ('4', 'DIARIA'), ('5', 'OTROS'),)
    PAYMENT_TYPE_CHOICES = (('1', 'EFECTIVO'), ('2', 'DEPÓSITO EN CUENTA'), ('3', 'OTROS'),)
    AGREEMENT_TO_AVOID_DOUBLE_TAXATION_CHOICES = (
        ('0', 'NINGUNO'), ('1', 'CANADA'), ('2', 'CHILE'), ('3', 'CAN'), ('4', 'BRASIL'),)
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, null=True, blank=True )
    labor_regime = models.ForeignKey('LaborRegime', on_delete=models.CASCADE)
    educational_situation = models.ForeignKey('EducationalSituation', on_delete=models.CASCADE)
    occupation_private_sector = models.ForeignKey(
        'OccupationPrivateSector', related_name='ops', on_delete=models.CASCADE, null=True, blank=True)
    occupation_public_sector = models.ForeignKey(
        'OccupationPublicSector', on_delete=models.CASCADE, null=True, blank=True)

    disability = models.BooleanField(default=False)
    cuspp = models.CharField(max_length=12, null=True, blank=True)
    sctr_pension = models.CharField(max_length=1, choices=SCTR_PENSION_CHOICES, default='0', )
    contract_type = models.ForeignKey('ContractType', on_delete=models.CASCADE)
    subject_to_atypical_regime = models.BooleanField(default=False)
    subject_to_maximum_working_day = models.BooleanField(default=False)
    subject_to_night_time = models.BooleanField(default=False)
    is_unionized = models.BooleanField(default=False)
    periodicity = models.CharField(max_length=1, choices=PERIODICITY_CHOICES, default='1', )
    initial_basic_remuneration = models.DecimalField(max_digits=10, decimal_places=2, default='0',)
    situation = models.ForeignKey('Situation', on_delete=models.CASCADE, null=True)
    exempted_5th_category_rent = models.BooleanField(default=False)
    special_situation = models.ForeignKey('SpecialSituation', on_delete=models.CASCADE, null=True)
    payment_type = models.CharField(max_length=1, choices=PAYMENT_TYPE_CHOICES, default='1', )
    occupational_category = models.ForeignKey(
        'OccupationalCategory', on_delete=models.CASCADE, null=True)
    agreement_to_avoid_double_taxation = models.CharField(
        max_length=1, choices=AGREEMENT_TO_AVOID_DOUBLE_TAXATION_CHOICES, default='0', )
    # Solo para los CAS (tipo de trabajador = 67).
    ruc = models.CharField(max_length=11, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

    def get_worker_type(self):
        worker_type = None
        period_obj2 = Period.objects.filter(worker=self, category='1', register_type='2').last()
        if period_obj2:
            worker_type = period_obj2.worker_type
        return worker_type

    def get_health_insurance_regime(self):
        health_insurance_regime = None
        period_obj3 = Period.objects.filter(worker=self, category='1', register_type='3').last()
        if period_obj3:
            health_insurance_regime = period_obj3.health_insurance_regime
        return health_insurance_regime

    def get_pensioner_regime(self):
        pensioner_regime = None
        period_obj4 = Period.objects.filter(worker=self, category='1', register_type='4').last()
        if period_obj4:
            pensioner_regime = period_obj4.pensioner_regime
        return pensioner_regime

    class Meta:
        verbose_name = 'Datos del trabajador'
        verbose_name_plural = 'Datos de los trabajadores'


class LaborTrainingModalityType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Tipo de modalidad formativa laboral y otros'
        verbose_name_plural = 'Tipos de modalidad formativa laboral y otros'


class StaffInTraining(models.Model):
    MEDICAL_INSURANCE_CHOICES = (('1', 'ESSALUD'), ('2', 'Seguro Privado'),)
    VOCATIONAL_TRAINING_CENTER_CHOICES = (
        ('1', 'Centro Educativo'), ('2', 'Universidad'), ('3', 'Instituto'), ('4', 'Otros'),)
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, null=True, blank=True )
    labor_training_modality_type = models.ForeignKey(
        'LaborTrainingModalityType', on_delete=models.CASCADE)
    medical_insurance = models.CharField(
        max_length=1, choices=MEDICAL_INSURANCE_CHOICES, null=True,)
    educational_situation = models.ForeignKey('EducationalSituation', on_delete=models.CASCADE)
    occupation_private_sector = models.ForeignKey(
        'OccupationPrivateSector', on_delete=models.CASCADE, null=True)
    occupation_public_sector = models.ForeignKey(
        'OccupationPublicSector', on_delete=models.CASCADE, null=True)
    mother_with_family_responsibility = models.BooleanField(default=False)
    disability = models.BooleanField(default=False)
    vocational_training_center = models.CharField(
        max_length=1, choices=VOCATIONAL_TRAINING_CENTER_CHOICES, null=True,)
    subject_to_night_time_work = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.employee

    class Meta:
        verbose_name = 'Persona en formación'
        verbose_name_plural = 'Personal en formación'


class ThirdPartyPersonnel(models.Model):
    SCTR_PENSION_CHOICES = (('1', 'ONP'), ('2', 'Seguro Privado'),)
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, null=True, blank=True )
    employer_ruc_that_highlights_displaces_me = models.CharField(
        max_length=11, null=True, blank=True)
    sctr_pension = models.CharField(max_length=1, choices=SCTR_PENSION_CHOICES, null=True, )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.employee

    class Meta:
        verbose_name = 'Persona de tercero'
        verbose_name_plural = 'Personal de tercero'


class ReasonForWithdrawal(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Motivo de la baja del registro'
        verbose_name_plural = 'Motivos de baja del registro'


class WorkerType(models.Model):
    PRIVATE_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    PUBLIC_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    OTHER_ENTITIES_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)
    private_sector = models.CharField('Sector Privado', max_length=3,
                                      choices=PRIVATE_SECTOR_CHOICES, default='A', )
    public_sector = models.CharField('Sector Publico', max_length=3,
                                     choices=PUBLIC_SECTOR_CHOICES, default='A', )
    other_entities = models.CharField(
        'Otras entidades', max_length=3, choices=OTHER_ENTITIES_CHOICES, default='A', )

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Tipo de trabajador, pensionista o prestador de servicios'
        verbose_name_plural = 'Tipos de trabajadores'


class HealthInsuranceRegime(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Régimen de aseguramiento de salud'
        verbose_name_plural = 'Régimenes de aseguramiento de salud'


class PensionerRegime(models.Model):
    PRIVATE_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    PUBLIC_SECTOR_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    OTHER_ENTITIES_CHOICES = (('A', 'APLICA'), ('N.A', 'NO APLICA'),)
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=40, null=True, blank=True)
    private_sector = models.CharField('Sector Privado', max_length=3,
                                      choices=PRIVATE_SECTOR_CHOICES, default='A', )
    public_sector = models.CharField('Sector Publico', max_length=3,
                                     choices=PUBLIC_SECTOR_CHOICES, default='A', )
    other_entities = models.CharField(
        'Otras entidades', max_length=3, choices=OTHER_ENTITIES_CHOICES, default='A', )

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Régimen pensionario'
        verbose_name_plural = 'Régimenes pensionarios'


class Period(models.Model):
    CATEGORY_CHOICES = (('1', 'Trabajador'), ('2', 'Pensionista'),
                        ('4', 'Personal de Terceros'), ('5', 'Personal en Formación'),)
    REGISTER_TYPE_CHOICES = (('1', 'Período'), ('2', 'Tipo de trabajador'), (
        '3', 'Régimen de Aseguramiento de Salud'), ('4', 'Régimen pensionario'), ('5', 'SCTR Salud'),)
    SCTR_HEALTH_CHOICES = (('1', 'EsSalud'), ('2', 'EPS'),)
    id = models.AutoField(primary_key=True)
    worker = models.ForeignKey('Worker', on_delete=models.CASCADE, null=True, blank=True )
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES, null=True, )
    register_type = models.CharField(max_length=1, choices=REGISTER_TYPE_CHOICES, null=True, )

    start_or_restart_date = models.DateField(null=True, blank=True)
    ending_date = models.DateField(null=True, blank=True)
    indicator_of_the_type_of_registration = models.CharField(max_length=2, null=True, blank=True)
    reason_for_withdrawal = models.ForeignKey(
        'ReasonForWithdrawal', on_delete=models.CASCADE, null=True, blank=True)
    worker_type = models.ForeignKey('WorkerType', on_delete=models.CASCADE, null=True)
    health_insurance_regime = models.ForeignKey(
        'HealthInsuranceRegime', on_delete=models.CASCADE, null=True)
    pensioner_regime = models.ForeignKey('PensionerRegime', on_delete=models.CASCADE, null=True)
    sctr_health = models.CharField(max_length=2, choices=SCTR_HEALTH_CHOICES, null=True, )
    eps_own_services = models.CharField(max_length=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.employee

    class Meta:
        verbose_name = 'Datos de período'
        verbose_name_plural = 'Datos de períodos'


class Subsidiary(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    business_name = models.CharField('Razon social', max_length=45, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    contact_phone = models.CharField(max_length=45, null=True, blank=True)
    serial = models.CharField(max_length=4, null=True, blank=True)
    phone = models.CharField(max_length=45, null=True, blank=True)
    ruc = models.CharField(max_length=11)
    dgh = models.CharField(max_length=45, null=True, blank=True)
    legal_representative_name = models.CharField(max_length=100, null=True, blank=True)
    legal_representative_surname = models.CharField(max_length=100, null=True, blank=True)
    legal_representative_dni = models.CharField(max_length=45, null=True, blank=True)
    is_main = models.BooleanField('Sede principal', default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'


class Establishment(models.Model):
    id = models.AutoField(primary_key=True)
    worker = models.ForeignKey('Worker', on_delete=models.CASCADE, null=True, blank=True )
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE, null=True, blank=True)
    # ruc_own_or_the_employer_to_whom_i_highlight_or_displace_personal
    ruc_own = models.CharField(max_length=11, null=True, blank=True)
    # establishment_code = models.CharField(max_length=4, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Establecimiento donde labora el trabajador'
        verbose_name_plural = 'Establecimientos donde labora el trabajador'


class EducationalInstitutionsAndTheirCareers(models.Model):
    regime_id = models.IntegerField()
    regime_description = models.CharField(max_length=20, null=True, blank=True)
    institution_type_id = models.IntegerField()
    institution_type_description = models.CharField(max_length=200, null=True, blank=True)
    institution_id = models.CharField(max_length=9, null=True, blank=True)
    institution_description = models.CharField(max_length=250, null=True, blank=True)
    career_id = models.CharField(max_length=6, null=True, blank=True)
    career_description = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.institution_description

    class Meta:
        verbose_name = 'Institución educativa y sus carreras'
        verbose_name_plural = 'Instituciones educativas y sus carreras'


class StudiesCompleted(models.Model):
    COMPLETE_HIGHER_EDUCATION_CHOICES = (
        ('11', 'SUPERIOR COMPLETA  (INSTIT SUPER)'), ('13', 'UNIVERSITARIA COMPLETA'),)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, )
    complete_higher_education = models.CharField(
        max_length=2, choices=COMPLETE_HIGHER_EDUCATION_CHOICES, null=True, )
    # indicator_educational_institution_of_peru
    is_educational_institution_of_peru = models.BooleanField(default=True)
    educational_institution = models.ForeignKey(
        'EducationalInstitutionsAndTheirCareers', on_delete=models.CASCADE, )
    career_code = models.CharField(max_length=6, null=True, blank=True)
    senior_year = models.CharField(max_length=4, null=True, blank=True)

    def __str__(self):
        return self.employee

    class Meta:
        verbose_name = 'Datos de estudio concluido'
        verbose_name_plural = 'Datos de estudios concluidos'


class FinancialSystemEntity(models.Model):
    id = models.CharField(primary_key=True, max_length=3)
    description = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Entidad del sistema financiero'
        verbose_name_plural = 'Entidades del sistema financiero'


class PaymentAccountData(models.Model):
    id = models.AutoField(primary_key=True)
    worker = models.ForeignKey('Worker', on_delete=models.CASCADE, )
    financial_system_entity = models.ForeignKey('FinancialSystemEntity', on_delete=models.CASCADE, null=True, blank=True )
    account_number_where_the_remuneration_is_paid = models.CharField(max_length=14, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Dato de cuenta de abono'
        verbose_name_plural = 'Datos de cuenta de abono'


class FamilyBond(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=80, null=True, blank=True)
    short_description = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Vínculo familiar'
        verbose_name_plural = 'Vínculos familiares'


class DocumentTypeThatProvesTheLink(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    description = models.CharField(max_length=200, null=True, blank=True)
    short_description = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Tipo de Documento que acredita el vínculo'
        verbose_name_plural = 'Tipos de Documentos que acredita el vínculo'


class Beneficiary(models.Model):
    GENDER_CHOICES = (('1', 'masculino'), ('2', 'femenino'),)
    ESSALUD_ASSISTANCE_CHOICES = (('1', 'dirección 1'), ('2', ' dirección 2'),)
    id = models.AutoField(primary_key=True)
    worker = models.ForeignKey('Worker', on_delete=models.CASCADE, null=True, blank=True )
    document_type = models.ForeignKey('DocumentType', on_delete=models.CASCADE)
    document_number = models.CharField(max_length=15, null=True, blank=True)
    document_issuing_country = models.ForeignKey('DocumentIssuingCountry', on_delete=models.CASCADE)
    birthdate = models.DateField('Fecha de nacimiento', null=True, blank=True)
    paternal_last_name = models.CharField(max_length=40, null=True, blank=True)
    maternal_last_name = models.CharField(max_length=40, null=True, blank=True)
    names = models.CharField(max_length=40, null=True, blank=True)
    gender = models.CharField('Sexo', max_length=1, choices=GENDER_CHOICES, default='1', )
    family_bond = models.ForeignKey('FamilyBond', on_delete=models.CASCADE, )
    document_type_that_proves_the_link = models.ForeignKey('DocumentTypeThatProvesTheLink', on_delete=models.CASCADE, )
    document_number_that_proves_the_link = models.CharField(max_length=20, null=True, blank=True)
    conception_month = models.CharField(max_length=6, null=True, blank=True)

    address_1_road_type = models.ForeignKey(
        'RoadType', related_name='beneficiary_road_type_add_1', on_delete=models.SET_NULL, null=True, blank=True)
    address_1_road_name = models.CharField(max_length=20, null=True, blank=True)
    address_1_road_number = models.CharField(max_length=4, null=True, blank=True)
    address_1_department = models.CharField(max_length=4, null=True, blank=True)
    address_1_interior = models.CharField(max_length=4, null=True, blank=True)
    address_1_apple = models.CharField(max_length=4, null=True, blank=True)
    address_1_lot = models.CharField(max_length=4, null=True, blank=True)
    address_1_kilometer = models.CharField(max_length=4, null=True, blank=True)
    address_1_block = models.CharField(max_length=4, null=True, blank=True)
    address_1_stage = models.CharField(max_length=4, null=True, blank=True)
    address_1_zone_type = models.ForeignKey(
        'ZoneType', related_name='beneficiary_zone_type_add_1', on_delete=models.SET_NULL, null=True, blank=True)
    address_1_zone_name = models.CharField(max_length=20, null=True, blank=True)
    address_1_reference = models.CharField(max_length=40, null=True, blank=True)
    address_1_district = models.ForeignKey(
        'District', related_name='beneficiary_district_add_1', on_delete=models.SET_NULL, null=True, blank=True)

    address_2_road_type = models.ForeignKey(
        'RoadType', related_name='beneficiary_road_type_add_2', on_delete=models.SET_NULL, null=True, blank=True)
    address_2_road_name = models.CharField(max_length=20, null=True, blank=True)
    address_2_road_number = models.CharField(max_length=4, null=True, blank=True)
    address_2_department = models.CharField(max_length=4, null=True, blank=True)
    address_2_interior = models.CharField(max_length=4, null=True, blank=True)
    address_2_apple = models.CharField(max_length=4, null=True, blank=True)
    address_2_lot = models.CharField(max_length=4, null=True, blank=True)
    address_2_kilometer = models.CharField(max_length=4, null=True, blank=True)
    address_2_block = models.CharField(max_length=4, null=True, blank=True)
    address_2_stage = models.CharField(max_length=4, null=True, blank=True)
    address_2_zone_type = models.ForeignKey(
        'ZoneType', related_name='beneficiary_zone_type_add_2', on_delete=models.SET_NULL, null=True, blank=True)
    address_2_zone_name = models.CharField(max_length=20, null=True, blank=True)
    address_2_reference = models.CharField(max_length=40, null=True, blank=True)
    address_2_district = models.ForeignKey(
        'District', related_name='beneficiary_district_add_2', on_delete=models.SET_NULL, null=True, blank=True)

    essalud_assistance = models.CharField(
        'Centro asistencial', max_length=1, choices=ESSALUD_ASSISTANCE_CHOICES, default='1', )

    telephone_national_long_distance_code = models.ForeignKey(
        'TelephoneNationalLongDistanceCode', related_name='beneficiary_cldn', on_delete=models.SET_NULL, null=True, blank=True)
    telephone_number = models.CharField(max_length=9, null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.names

    class Meta:
        verbose_name = 'Derechohabiente'
        verbose_name_plural = 'Derechohabientes'
