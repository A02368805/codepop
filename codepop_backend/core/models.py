from django.db import models

REGION_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'), ('G', 'G')]


class Region(models.Model):
    code = models.CharField(max_length=1, choices=REGION_CHOICES, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"Region {self.code}"


class SupplyHub(models.Model):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='supply_hubs')
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)


class Store(models.Model):
    store_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='stores')
    is_active = models.BooleanField(default=True)


class ConflictLog(models.Model):
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=200)
    conflict_type = models.CharField(max_length=100)
    first_update_timestamp = models.DateTimeField()
    second_update_timestamp = models.DateTimeField()
    resolution = models.CharField(max_length=200)
    applied_value = models.TextField()
    discarded_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
