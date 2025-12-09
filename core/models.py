from django.db import models
from django.db.models import F, Sum
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password 

# --- Model Pelanggan (Hashing Password) ---
class Pelanggan(models.Model):
    idPelanggan = models.AutoField(primary_key=True, verbose_name='ID Pelanggan')
    nama = models.CharField(max_length=50, verbose_name='Nama Pelanggan')
    noWa = models.CharField(max_length=20, verbose_name='Nomor WhatsApp')
    alamat = models.CharField(max_length=200, verbose_name='Alamat')
    username = models.CharField(max_length=20, unique=True, verbose_name='Username')
    password = models.CharField(max_length=150, verbose_name='Password (Hash)')

    def save(self, *args, **kwargs):
        # Hash password jika belum di-hash (panjang 128 karakter atau lebih adalah indikasi hash)
        if len(self.password) < 128 or not self.password.startswith('pbkdf2_sha256'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        # Metode untuk memverifikasi password
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.nama
    
    class Meta:
        verbose_name = 'Pelanggan'
        verbose_name_plural = 'Pelanggan'

# --- Model Sopir (Hashing Password) ---
class Sopir(models.Model):
    idSopir = models.AutoField(primary_key=True, verbose_name='ID Sopir')
    nama = models.CharField(max_length=20, verbose_name='Nama Sopir')
    noHp = models.CharField(max_length=20, verbose_name='Nomor HP')
    username = models.CharField(max_length=20, unique=True, verbose_name='Username')
    password = models.CharField(max_length=150, verbose_name='Password (Hash)')

    def save(self, *args, **kwargs):
        # Hash password jika belum di-hash
        if len(self.password) < 128 or not self.password.startswith('pbkdf2_sha256'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        # Metode untuk memverifikasi password
        return check_password(raw_password, self.password)

    def __str__(self):
        return f'( {self.noHp} ) - {self.nama}'
    
    class Meta:
        verbose_name = 'Sopir'
        verbose_name_plural = 'Sopir'

# --- Model Kendarann ---
class Kendaraan(models.Model):
    JENIS_CHOICES = (
        ('Roda 4', 'Roda 4'), 
        ('Roda 6', 'Roda 6')
    )
    nomorPlat = models.CharField(max_length=15, primary_key=True, verbose_name='Nomor Plat')
    nama = models.CharField(max_length=20, verbose_name='Nama Kendaraan')
    # Perbaiki format choices
    jenis = models.CharField(max_length=15, choices=JENIS_CHOICES, default='Roda 4', verbose_name='Jenis Kendaraan') 
    # Gunakan models.PROTECT untuk keamanan relasi
    idSopir = models.ForeignKey(Sopir, on_delete=models.PROTECT, verbose_name='Nama Sopir') 

    def __str__(self):
        return f'( {self.nomorPlat} ) - {self.nama}'
    
    class Meta:
        verbose_name = 'Kendaraan'
        verbose_name_plural = 'Kendaraan'

# --- Model Produk ---
class Produk(models.Model):
    idProduk = models.AutoField(primary_key=True, verbose_name='ID Produk')
    namaProduk = models.CharField(max_length=30, verbose_name='Nama Produk')
    ukuranKemasan = models.CharField(max_length=20, verbose_name='Ukuran Kemasan')
    hargaPerDus = models.PositiveIntegerField(verbose_name='Harga per Dus')
    # Tambahkan default=0 agar stok selalu positif
    stok = models.PositiveIntegerField(default=0, verbose_name='Stok Saat Ini') 
    deskripsi = models.CharField(max_length=200, blank=True, verbose_name='Deskripsi')
    foto = models.ImageField(upload_to='foto_produk/', null=True, blank=True, verbose_name='Foto Produk')
    
    
    def __str__(self):
        return f'{self.namaProduk} - ({self.stok})'
    
    class Meta:
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'

# --- Model StokMasuk (Logic Otomatis: Menambah Stok Produk) ---
class StokMasuk(models.Model):
    idStok = models.AutoField(primary_key=True, verbose_name='ID Stok Masuk')
    idProduk = models.ForeignKey(Produk, on_delete=models.PROTECT, verbose_name='Produk')
    jumlah = models.PositiveIntegerField(verbose_name='Jumlah Masuk')
    # Ubah ke auto_now_add=True agar tanggal tercatat saat pembuatan
    tanggal = models.DateField(auto_now_add=True, verbose_name='Tanggal Masuk') 
    keterangan = models.CharField(max_length=200, blank=True, verbose_name='Keterangan')
    
    def __init__(self, *args, **kwargs):
        # Simpan nilai awal jumlah untuk operasi update
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah if self.pk else 0
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            # Tambahkan stok jika entri baru
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
        else:
            # Hitung perbedaan dan perbarui stok saat diubah
            perbedaan_jumlah = self.jumlah - self.__original_jumlah
            if perbedaan_jumlah != 0:
                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + perbedaan_jumlah)
        
        self.__original_jumlah = self.jumlah

    def delete(self, *args, **kwargs):
        # Kurangi stok jika entri dihapus
        Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - self.jumlah)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.tanggal} - {self.idProduk.namaProduk}'
    
    class Meta:
        verbose_name = 'Stok Masuk'
        verbose_name_plural = 'Stok Masuk'
    
# --- Model Pemesanan (Logic Otomatis: Memperbarui Total) ---
class Pemesanan(models.Model):
    STATUS_CHOICES = [
        ('Diproses', 'Diproses'),
        ('Dikirim', 'Dikirim'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]
    
    idPemesanan = models.AutoField(primary_key=True, verbose_name='ID Pemesanan')
    # Gunakan models.PROTECT untuk keamanan relasi
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.PROTECT, verbose_name='Pelanggan') 
    tanggalPemesanan = models.DateTimeField(auto_now_add=True, verbose_name='Tanggal Pemesanan')
    alamatPengiriman = models.CharField(max_length=200, verbose_name='Alamat Pengiriman')
    # Tambahkan default=0.00
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Total Harga') 
    buktiBayar = models.ImageField(upload_to='bukti_pembayaran/', null=True, blank=True, verbose_name='Bukti Pembayaran')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='Diproses', verbose_name='Status Pemesanan')
    fotoPengiriman = models.ImageField(upload_to='bukti_pengiriman/', null=True, blank=True, verbose_name='Foto Pengiriman')
    # Gunakan models.SET_NULL agar pesanan tetap ada jika Sopir dihapus
    idSopir = models.ForeignKey(Sopir, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Sopir Pengirim') 
    
    def update_total(self):
        # Hitung total dari subTotal semua DetailPemesanan
        total_subtotal = self.detailpemesanan_set.aggregate(Sum('subTotal'))['subTotal__sum']
        self.total = total_subtotal if total_subtotal is not None else 0.00
        # Gunakan update_fields untuk menghindari rekursif save
        self.save(update_fields=['total']) 
    
    def __str__(self):
        return f'{self.tanggalPemesanan.strftime("%Y-%m-%d %H:%M")} - {self.idPelanggan.nama}'
    
    class Meta:
        verbose_name = 'Pemesanan'
        verbose_name_plural = 'Pemesanan'


# --- Model DetailPemesanan (Logic Otomatis: SubTotal & Mengurangi Stok) ---
class DetailPemesanan(models.Model):
    idDetail = models.AutoField(primary_key=True, verbose_name='ID Detail')
    idPemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE, verbose_name='ID Pemesanan')
    idProduk = models.ForeignKey(Produk, on_delete=models.PROTECT, verbose_name='Produk')
    jumlah = models.PositiveIntegerField(verbose_name='Jumlah Pesanan')
    # Tambahkan default=0.00
    subTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Sub Total') 
    
    def __init__(self, *args, **kwargs):
        # Simpan nilai awal jumlah untuk operasi update stok
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah if self.pk else 0
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        # 1. Perhitungan SubTotal (Otomasi)
        harga_produk = self.idProduk.hargaPerDus
        self.subTotal = harga_produk * self.jumlah
        
        super().save(*args, **kwargs)
        
        # 2. Pengurangan/Penyesuaian Stok (Otomasi)
        if self.idPemesanan.status != 'Dibatalkan':
            perbedaan_jumlah = self.jumlah - self.__original_jumlah
            
            if perbedaan_jumlah != 0:
                # Pastikan stok mencukupi
                if self.idProduk.stok < perbedaan_jumlah:
                    raise ValidationError(f'Stok {self.idProduk.namaProduk} tidak mencukupi ({self.idProduk.stok}).')

                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - perbedaan_jumlah)
            
            self.__original_jumlah = self.jumlah
            
        # 3. Perbarui Total Pemesanan Induk (Otomasi)
        self.idPemesanan.update_total()

    def delete(self, *args, **kwargs):
        # Tambahkan kembali stok saat detail pesanan dihapus
        if self.idPemesanan.status != 'Dibatalkan':
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
            
        super().delete(*args, **kwargs)
        # Perbarui Total Pemesanan Induk
        self.idPemesanan.update_total()
    
    def __str__(self):
        return f'Detail {self.idDetail}'
    
    class Meta:
        verbose_name = 'Detail Pemesanan'
        verbose_name_plural = 'Detail Pemesanan'
        
# --- Model Feedback ---
class Feedback(models.Model):
    idFeedback = models.AutoField(primary_key=True, verbose_name='ID Feedback')
    # Gunakan models.CASCADE untuk menghapus feedback jika pelanggan dihapus
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE, verbose_name='Pelanggan') 
    # Perbaiki nama field yang duplikat menjadi 'isi'
    isi = models.TextField(verbose_name='Isi Feedback') 
    tanggal = models.DateTimeField(auto_now_add=True, verbose_name='Tanggal Feedback')
    
    def __str__(self):
        # Tampilkan nama Pelanggan, bukan objek Pelanggan
        return f'{self.idPelanggan.nama} - {self.tanggal.strftime("%Y-%m-%d")}'
    
    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'