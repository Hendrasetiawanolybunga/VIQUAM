from django.db import models
from django.db.models import F, Sum
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password 

class Pelanggan(models.Model):
    idPelanggan = models.AutoField(primary_key=True, verbose_name='ID Pelanggan')
    nama = models.CharField(max_length=50, verbose_name='Nama Pelanggan')
    noWa = models.CharField(max_length=20, verbose_name='Nomor WhatsApp')
    alamat = models.CharField(max_length=200, verbose_name='Alamat Tempat Tinggal')
    username = models.CharField(max_length=20, unique=True, verbose_name='Username')
    password = models.CharField(max_length=150, verbose_name='Password (Hash)')

    def save(self, *args, **kwargs):
        if len(self.password) < 128 or not self.password.startswith('pbkdf2_sha256'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.nama
    
    class Meta:
        verbose_name = 'Pelanggan'
        verbose_name_plural = 'Pelanggan'

class Sopir(models.Model):
    idSopir = models.AutoField(primary_key=True, verbose_name='ID Sopir')
    nama = models.CharField(max_length=20, verbose_name='Nama Sopir')
    noHp = models.CharField(max_length=20, verbose_name='Nomor HP')
    username = models.CharField(max_length=20, unique=True, verbose_name='Username')
    password = models.CharField(max_length=150, verbose_name='Password (Hash)')

    def save(self, *args, **kwargs):
        if len(self.password) < 128 or not self.password.startswith('pbkdf2_sha256'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f'( {self.noHp} ) - {self.nama}'
    
    class Meta:
        verbose_name = 'Sopir'
        verbose_name_plural = 'Sopir'

class Kendaraan(models.Model):
    JENIS_CHOICES = (
        ('Roda 4', 'Roda 4'), 
        ('Roda 6', 'Roda 6')
    )
    nomorPlat = models.CharField(max_length=15, primary_key=True, verbose_name='Nomor Plat')
    nama = models.CharField(max_length=20, verbose_name='Nama Kendaraan')
    jenis = models.CharField(max_length=15, choices=JENIS_CHOICES, default='Roda 4', verbose_name='Jenis Kendaraan') 
    idSopir = models.ForeignKey(Sopir, on_delete=models.PROTECT, verbose_name='Nama Sopir') 

    def __str__(self):
        return f'( {self.nomorPlat} ) - {self.nama}'
    
    class Meta:
        verbose_name = 'Kendaraan'
        verbose_name_plural = 'Kendaraan'

class Produk(models.Model):
    idProduk = models.AutoField(primary_key=True, verbose_name='ID Produk')
    namaProduk = models.CharField(max_length=30, verbose_name='Nama Produk')
    ukuranKemasan = models.CharField(max_length=20, verbose_name='Ukuran Kemasan')
    hargaPerDus = models.PositiveIntegerField(verbose_name='Harga per Dus/Galon')
    stok = models.PositiveIntegerField(verbose_name='Stok Saat Ini') 
    deskripsi = models.CharField(max_length=200, blank=True, verbose_name='Deskripsi')
    foto = models.ImageField(upload_to='foto_produk/', null=True, blank=True, verbose_name='Foto Produk')
    
    def __str__(self):
        return f'{self.namaProduk} - ({self.stok})'
    
    class Meta:
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'

class StokMasuk(models.Model):
    idStok = models.AutoField(primary_key=True, verbose_name='ID Stok Masuk')
    idProduk = models.ForeignKey(Produk, on_delete=models.PROTECT, verbose_name='Produk')
    jumlah = models.PositiveIntegerField(verbose_name='Jumlah Masuk')
    tanggal = models.DateField(auto_now_add=True, verbose_name='Tanggal Masuk') 
    keterangan = models.CharField(max_length=200, blank=True, verbose_name='Keterangan')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah if self.pk else 0
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
        else:
            perbedaan_jumlah = self.jumlah - self.__original_jumlah
            if perbedaan_jumlah != 0:
                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + perbedaan_jumlah)
        
        self.__original_jumlah = self.jumlah

    def delete(self, *args, **kwargs):
        Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - self.jumlah)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.tanggal} - {self.idProduk.namaProduk}'
    
    class Meta:
        verbose_name = 'Stok Masuk'
        verbose_name_plural = 'Stok Masuk'
    
class Pemesanan(models.Model):
    STATUS_CHOICES = [
        ('Diproses', 'Diproses'),
        ('Dikirim', 'Dikirim'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]
    
    idPemesanan = models.AutoField(primary_key=True, verbose_name='ID Pemesanan')
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.PROTECT, verbose_name='Pelanggan') 
    tanggalPemesanan = models.DateTimeField(auto_now_add=True, verbose_name='Tanggal Pemesanan')
    alamatPengiriman = models.CharField(max_length=200, verbose_name='Alamat Pengiriman')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Total Harga') 
    buktiBayar = models.ImageField(upload_to='bukti_pembayaran/', null=True, blank=True, verbose_name='Bukti Pembayaran')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='Diproses', verbose_name='Status Pemesanan')
    fotoPengiriman = models.ImageField(upload_to='bukti_pengiriman/', null=True, blank=True, verbose_name='Foto Pengiriman')
    idSopir = models.ForeignKey(Sopir, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Sopir Pengirim') 
    
    def update_total(self):
        total_subtotal = self.detailpemesanan_set.aggregate(Sum('subTotal'))['subTotal__sum']
        self.total = total_subtotal if total_subtotal is not None else 0.00
        self.save(update_fields=['total']) 
    
    def __str__(self):
        return f'{self.tanggalPemesanan.strftime("%Y-%m-%d %H:%M")} - {self.idPelanggan.nama}'
    
    class Meta:
        verbose_name = 'Pemesanan'
        verbose_name_plural = 'Pemesanan'

class DetailPemesanan(models.Model):
    idDetail = models.AutoField(primary_key=True, verbose_name='ID Detail')
    idPemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE, verbose_name='ID Pemesanan')
    idProduk = models.ForeignKey(Produk, on_delete=models.PROTECT, verbose_name='Produk')
    jumlah = models.PositiveIntegerField(verbose_name='Jumlah Pesanan')
    subTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Sub Total') 
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah if self.pk else 0
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        harga_produk = self.idProduk.hargaPerDus
        self.subTotal = harga_produk * self.jumlah
        
        super().save(*args, **kwargs)
        
        if self.idPemesanan.status != 'Dibatalkan':
            perbedaan_jumlah = self.jumlah - self.__original_jumlah
            
            if perbedaan_jumlah != 0:
                if self.idProduk.stok < perbedaan_jumlah:
                    raise ValidationError(f'Stok {self.idProduk.namaProduk} tidak mencukupi ({self.idProduk.stok}).')

                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - perbedaan_jumlah)
            
            self.__original_jumlah = self.jumlah
            
        self.idPemesanan.update_total()

    def delete(self, *args, **kwargs):
        if self.idPemesanan.status != 'Dibatalkan':
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
            
        super().delete(*args, **kwargs)
        self.idPemesanan.update_total()
    
    def __str__(self):
        return f'Detail {self.idDetail}'
    
    class Meta:
        verbose_name = 'Detail Pemesanan'
        verbose_name_plural = 'Detail Pemesanan'
        
class Feedback(models.Model):
    idFeedback = models.AutoField(primary_key=True, verbose_name='ID Feedback')
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE, verbose_name='Pelanggan') 
    isi = models.TextField(verbose_name='Isi Feedback') 
    tanggal = models.DateTimeField(auto_now_add=True, verbose_name='Tanggal Feedback')
    
    def __str__(self):
        return f'{self.idPelanggan.nama} - {self.tanggal.strftime("%Y-%m-%d")}'
    
    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'