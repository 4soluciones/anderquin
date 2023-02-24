from django.db import models
from django.contrib.auth.models import User
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust


# Create your models here.


class Subsidiary(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    address = models.CharField(max_length=200)
    serie = models.CharField(max_length=200)
    status = models.BooleanField('Estado', default=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(verbose_name='Descripción',
                                   max_length=200, null=True, blank=True)
    subsidiary = models.ForeignKey('Subsidiary', on_delete=models.CASCADE)
    status = models.BooleanField('Estado', default=True)

    def __str__(self):
        return self.name


class Complement(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Complemento'
        verbose_name_plural = 'Complementos'


class Subcategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    status = models.BooleanField('Estado', default=True)
    image = models.ImageField(upload_to='subcategory/', default='pic_folder/None/no-img.jpg')
    image_thumbnail = ImageSpecField([Adjust(contrast=1.2, sharpness=1.1), ResizeToFill(
        100, 100)], source='image', format='JPEG', options={'quality': 90})
    complement = models.ManyToManyField(Complement, related_name='complements', blank=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'


class Dish(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    image = models.ImageField(upload_to='pic_folder/', default='pic_folder/None/no-img.jpg')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subcategory = models.ForeignKey(
        'Subcategory', on_delete=models.CASCADE, verbose_name="related subcategory")
    quantity = models.IntegerField()
    status = models.BooleanField('Estado', default=True)
    image_thumbnail = ImageSpecField([Adjust(contrast=1.2, sharpness=1.1), ResizeToFill(
        100, 100)], source='image', format='JPEG', options={'quality': 90})

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Plato'
        verbose_name_plural = 'Platos'


class Person(models.Model):
    id = models.AutoField(primary_key=True)
    names = models.CharField(max_length=100)
    paternal_last_name = models.CharField(max_length=40)
    maternal_last_name = models.CharField(max_length=40)
    telephone_number = models.CharField('Telefono', max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.id


class Employee(models.Model):
    person = models.OneToOneField('Person', on_delete=models.CASCADE, primary_key=True, )
    document_number = models.CharField(max_length=20)
    birthdate = models.DateField('Fecha de nacimiento', null=True, blank=True)
    photo = models.ImageField(upload_to='employee_photo/',default='employee_photo/img_employee.jpg', blank=True)
    photo_thumbnail = ImageSpecField([Adjust(contrast=1.2, sharpness=1.1), ResizeToFill(
        100, 100)], source='photo', format='JPEG', options={'quality': 90})
    occupation = models.ForeignKey('Occupation', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey('Subsidiary', on_delete=models.CASCADE)
    enabled = models.BooleanField('Habilitado', default=True)

    def __str__(self):
        return self.document_number

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'


class Occupation(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Ocupacion'
        verbose_name_plural = 'Ocupaciones'


class Customer(models.Model):
    person = models.OneToOneField('Person', on_delete=models.CASCADE, primary_key=True, )
    enabled = models.BooleanField('Habilitado', default=True)


class Address(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    address = models.CharField(max_length=500)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)


class CreditCard(models.Model):
    cc_number = models.CharField(max_length=200)
    cc_type = models.CharField(max_length=20)
    holder_name = models.CharField('Nombre del titular', max_length=40)
    company = models.CharField('Entidad', max_length=40)
    expire_date = models.DateField('Fecha de expiracion', null=True, blank=True)


class CustomerAccount(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    credit_card = models.ForeignKey('CreditCard', on_delete=models.CASCADE)


class Order(models.Model):
    STATUS_CHOICES = (('N', 'Nueva'), ('P', 'Preparando'), ('S', 'Enviado'),
                      ('D', 'Entregado'), ('C', 'Cerrado'),)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    correlative = models.IntegerField(default=0, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='N', )
    delivery_address = models.ForeignKey('Address', on_delete=models.CASCADE, null=True)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    credit_card = models.ForeignKey('CreditCard', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)


class OrderDish(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    dish = models.ForeignKey('Dish', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
